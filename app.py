from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from time import perf_counter

import psycopg
from flask import Flask, jsonify, render_template, request
from neo4j import GraphDatabase
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)

# Pastas e arquivos do projeto.
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
CURRICULO_JSON = DATABASE_DIR / "curriculo.json"
IMPORTADOR_POSTGRES = DATABASE_DIR / "importar_postgres.py"
IMPORTADOR_NEO4J = DATABASE_DIR / "importar_neo4j.py"

# Conexões dos bancos.
MONGO = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=3000)
COLECAO = MONGO["tads_curricular"]["cursos"]

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "tads_dev_123")
NEO4J = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "host=localhost port=5432 dbname=tads user=tads password=tads_dev",
)


def normalizar_lista(valor):
    """Aceita lista ou texto com códigos separados por vírgula."""
    if valor is None or valor == "":
        return []
    if isinstance(valor, str):
        valor = valor.split(",")
    if not isinstance(valor, list):
        raise ValueError("Os pré-requisitos devem ser uma lista de códigos.")
    return list(dict.fromkeys(str(item).strip() for item in valor if str(item).strip()))


def validar_curriculo(dados):
    if not isinstance(dados, dict):
        raise ValueError("O corpo enviado precisa ser um objeto JSON.")

    curso = dados.get("curso")
    disciplinas = dados.get("disciplinas")
    if not isinstance(curso, dict):
        raise ValueError("Informe os dados do curso.")
    if not str(curso.get("nome", "")).strip():
        raise ValueError("Informe o nome do curso.")
    if not str(curso.get("instituicao", "")).strip():
        raise ValueError("Informe a instituição.")
    if not isinstance(disciplinas, list) or not disciplinas:
        raise ValueError("Cadastre pelo menos uma disciplina.")

    codigos = set()
    normalizadas = []
    for indice, disciplina in enumerate(disciplinas, start=1):
        if not isinstance(disciplina, dict):
            raise ValueError(f"A disciplina {indice} está inválida.")

        codigo = str(disciplina.get("codigo", "")).strip()
        nome = str(disciplina.get("nome", "")).strip()
        if not codigo or not nome:
            raise ValueError(f"Preencha o código e o nome da disciplina {indice}.")
        if codigo in codigos:
            raise ValueError(f"O código {codigo} foi informado mais de uma vez.")
        codigos.add(codigo)

        try:
            creditos = int(disciplina.get("creditos", 0))
        except (TypeError, ValueError):
            raise ValueError(f"Os créditos de {codigo} precisam ser um número inteiro.")
        if creditos <= 0:
            raise ValueError(f"Os créditos de {codigo} precisam ser maiores que zero.")

        normalizadas.append({
            "codigo": codigo,
            "nome": nome,
            "creditos": creditos,
            "pre_requisitos": normalizar_lista(disciplina.get("pre_requisitos", [])),
            "pre_requisitos_alternativos": normalizar_lista(
                disciplina.get("pre_requisitos_alternativos", [])
            ),
        })

    codigos_validos = {d["codigo"] for d in normalizadas}
    for disciplina in normalizadas:
        todos = disciplina["pre_requisitos"] + disciplina["pre_requisitos_alternativos"]
        faltantes = sorted(set(todos) - codigos_validos)
        if faltantes:
            raise ValueError(
                f"Pré-requisito(s) não encontrado(s) para {disciplina['codigo']}: "
                + ", ".join(faltantes)
            )
        if disciplina["codigo"] in todos:
            raise ValueError(f"A disciplina {disciplina['codigo']} não pode ser pré-requisito dela mesma.")

    return {
        "curso": {
            "nome": str(curso["nome"]).strip(),
            "instituicao": str(curso["instituicao"]).strip(),
        },
        "disciplinas": normalizadas,
    }


def consultar_postgres(busca):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.codigo,
                    d.nome,
                    d.creditos,
                    COALESCE(
                        ARRAY_AGG(DISTINCT p.codigo)
                        FILTER (WHERE p.codigo IS NOT NULL),
                        ARRAY[]::VARCHAR[]
                    ) AS pre_requisitos,
                    COALESCE(
                        ARRAY_AGG(DISTINCT pa.codigo)
                        FILTER (WHERE pa.codigo IS NOT NULL),
                        ARRAY[]::VARCHAR[]
                    ) AS pre_requisitos_alternativos
                FROM disciplinas d
                LEFT JOIN pre_requisitos pr ON pr.disciplina_id = d.id
                LEFT JOIN disciplinas p ON p.id = pr.requisito_id
                LEFT JOIN pre_requisitos_alternativos pra ON pra.disciplina_id = d.id
                LEFT JOIN disciplinas pa ON pa.id = pra.requisito_id
                WHERE d.codigo ILIKE %s OR d.nome ILIKE %s
                GROUP BY d.id, d.codigo, d.nome, d.creditos
                ORDER BY d.codigo
                LIMIT 50
                """,
                (f"%{busca}%", f"%{busca}%"),
            )
            colunas = [desc.name for desc in cur.description]
            return [dict(zip(colunas, linha)) for linha in cur.fetchall()]


def consultar_mongodb(busca):
    regex = {"$regex": busca, "$options": "i"}
    documentos = COLECAO.find(
        {"disciplinas": {"$elemMatch": {"$or": [{"codigo": regex}, {"nome": regex}]}}},
        {"_id": 0, "curso": 1, "disciplinas": 1},
    )
    resultados = []
    for documento in documentos:
        for disciplina in documento.get("disciplinas", []):
            if busca.lower() in str(disciplina.get("codigo", "")).lower() or busca.lower() in str(disciplina.get("nome", "")).lower():
                resultados.append({
                    "codigo": disciplina.get("codigo", ""),
                    "nome": disciplina.get("nome", ""),
                    "creditos": disciplina.get("creditos", 0),
                    "pre_requisitos": disciplina.get("pre_requisitos", []),
                    "pre_requisitos_alternativos": disciplina.get("pre_requisitos_alternativos", []),
                })
    return sorted(resultados, key=lambda item: item["codigo"])


def consultar_neo4j(busca):
    consulta = """
        MATCH (d:Disciplina)
        WHERE toLower(d.codigo) CONTAINS toLower($busca)
           OR toLower(d.nome) CONTAINS toLower($busca)
        OPTIONAL MATCH (r:Disciplina)-[:PRE_REQUISITO_DE]->(d)
        WITH d, collect(DISTINCT r.codigo) AS pre_requisitos
        OPTIONAL MATCH (a:Disciplina)-[:PRE_REQUISITO_ALTERNATIVO_DE]->(d)
        RETURN
            d.codigo AS codigo,
            d.nome AS nome,
            coalesce(d.creditos, 0) AS creditos,
            pre_requisitos,
            collect(DISTINCT a.codigo) AS pre_requisitos_alternativos
        ORDER BY codigo
        LIMIT 50
    """
    with NEO4J.session() as session:
        resultado = session.run(consulta, busca=busca)
        return [registro.data() for registro in resultado]


def sincronizar_mongodb(dados):
    """Mantém um documento do curso com as disciplinas embutidas."""
    documento = {
        "curso": dados["curso"],
        "disciplinas": dados["disciplinas"],
    }
    COLECAO.replace_one({"curso.nome": dados["curso"]["nome"]}, documento, upsert=True)


def executar_importador(caminho):
    if not caminho.exists():
        raise FileNotFoundError(
            f"Não encontrei {caminho}. Confira se os importadores estão na pasta database."
        )
    ambiente = os.environ.copy()
    ambiente["PYTHONUTF8"] = "1"
    processo = subprocess.run(
        [sys.executable, str(caminho)],
        cwd=str(caminho.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ambiente,
        check=False,
    )
    if processo.returncode != 0:
        detalhe = (processo.stderr or processo.stdout or "Sem detalhes do importador.").strip()
        raise RuntimeError(f"Falha ao executar {caminho.name}:\n{detalhe}")
    return (processo.stdout or "").strip()


@app.route("/")
def inicio():
    return render_template("index.html")


@app.post("/api/consultar")
def consultar():
    dados = request.get_json(silent=True) or {}
    banco = str(dados.get("banco", "")).strip().lower()
    busca = str(dados.get("busca", "")).strip()

    consultas = {
        "relacional": consultar_postgres,
        "documental": consultar_mongodb,
        "grafo": consultar_neo4j,
    }
    if banco not in consultas:
        return jsonify({"erro": "Selecione um banco válido."}), 400
    if not busca:
        return jsonify({"erro": "Digite um código ou nome para pesquisar."}), 400

    inicio_tempo = perf_counter()
    try:
        resultados = consultas[banco](busca)
        duracao_ms = round((perf_counter() - inicio_tempo) * 1000, 3)
        return jsonify({"resultados": resultados, "tempo_ms": duracao_ms})
    except Exception as erro:
        app.logger.exception("Erro ao consultar %s", banco)
        return jsonify({"erro": f"Erro ao consultar {banco}: {erro}"}), 500


@app.post("/api/cadastrar-curso")
def cadastrar_curso():
    try:
        dados = validar_curriculo(request.get_json(silent=True) or {})

        # Salva o JSON primeiro: ele é a fonte de verdade dos dados curriculares.
        CURRICULO_JSON.parent.mkdir(parents=True, exist_ok=True)
        CURRICULO_JSON.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Atualiza o banco documental e executa os importadores dos outros bancos.
        sincronizar_mongodb(dados)
        saida_postgres = executar_importador(IMPORTADOR_POSTGRES)
        saida_neo4j = executar_importador(IMPORTADOR_NEO4J)

        return jsonify({
            "mensagem": "Currículo salvo no JSON e sincronizado com os bancos.",
            "arquivo": str(CURRICULO_JSON.relative_to(BASE_DIR)),
            "postgres": saida_postgres,
            "neo4j": saida_neo4j,
        }), 201
    except (ValueError, FileNotFoundError, RuntimeError, PyMongoError) as erro:
        app.logger.exception("Erro ao cadastrar/sincronizar currículo")
        return jsonify({"erro": str(erro)}), 400
    except Exception as erro:
        app.logger.exception("Erro inesperado ao cadastrar/sincronizar currículo")
        return jsonify({"erro": f"Erro inesperado: {erro}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
