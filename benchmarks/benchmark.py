
import csv
import json
import os
import statistics
import time
from pathlib import Path

import psycopg
from pymongo import MongoClient
from neo4j import GraphDatabase


# Caminhos e configurações dos bancos
BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_JSON = BASE_DIR / "database" / "curriculo.json"
ARQUIVO_RESULTADOS = BASE_DIR / "benchmarks" / "resultados_benchmark.csv"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "host=localhost port=5432 dbname=tads user=tads password=tads_dev",
)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "tads_dev_123")

REPETICOES = 30
AQUECIMENTO = 3


def consultar_postgres(conn, busca):
    # Pesquisa por código ou nome e recupera os pré-requisitos.
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
            LEFT JOIN pre_requisitos_alternativos pra
                ON pra.disciplina_id = d.id
            LEFT JOIN disciplinas pa ON pa.id = pra.requisito_id
            WHERE d.codigo ILIKE %s OR d.nome ILIKE %s
            GROUP BY d.id, d.codigo, d.nome, d.creditos
            ORDER BY d.codigo
            LIMIT 50
            """,
            (f"%{busca}%", f"%{busca}%"),
        )
        return cur.fetchall()


def consultar_mongodb(colecao, busca):
    regex = {"$regex": busca, "$options": "i"}

    documentos = colecao.find(
        {
            "disciplinas": {
                "$elemMatch": {
                    "$or": [{"codigo": regex}, {"nome": regex}]
                }
            }
        },
        {"_id": 0, "curso": 1, "disciplinas": 1},
    )

    resultados = []

    for documento in documentos:
        for disciplina in documento.get("disciplinas", []):
            codigo = str(disciplina.get("codigo", ""))
            nome = str(disciplina.get("nome", ""))

            if (
                busca.lower() in codigo.lower()
                or busca.lower() in nome.lower()
            ):
                resultados.append(disciplina)

    return sorted(resultados, key=lambda item: item.get("codigo", ""))


def consultar_neo4j(session, busca):
    consulta = """
        MATCH (d:Disciplina)
        WHERE toLower(d.codigo) CONTAINS toLower($busca)
           OR toLower(d.nome) CONTAINS toLower($busca)
        OPTIONAL MATCH (r:Disciplina)-[:PRE_REQUISITO_DE]->(d)
        WITH d, collect(DISTINCT r.codigo) AS pre_requisitos
        OPTIONAL MATCH
            (a:Disciplina)-[:PRE_REQUISITO_ALTERNATIVO_DE]->(d)
        RETURN
            d.codigo AS codigo,
            d.nome AS nome,
            coalesce(d.creditos, 0) AS creditos,
            pre_requisitos,
            collect(DISTINCT a.codigo) AS pre_requisitos_alternativos
        ORDER BY codigo
        LIMIT 50
    """

    resultado = session.run(consulta, busca=busca)
    return [registro.data() for registro in resultado]


def medir(nome_banco, funcao, busca):
    # Executa algumas consultas antes de começar a cronometrar.
    for _ in range(AQUECIMENTO):
        funcao(busca)

    tempos = []
    quantidade = 0

    for _ in range(REPETICOES):
        inicio = time.perf_counter_ns()
        resultados = funcao(busca)
        fim = time.perf_counter_ns()

        tempos.append((fim - inicio) / 1_000_000)
        quantidade = len(resultados)

    return {
        "banco": nome_banco,
        "busca": busca,
        "resultados": quantidade,
        "repeticoes": REPETICOES,
        "media_ms": round(statistics.mean(tempos), 4),
        "mediana_ms": round(statistics.median(tempos), 4),
        "minimo_ms": round(min(tempos), 4),
        "maximo_ms": round(max(tempos), 4),
    }


def main():
    with ARQUIVO_JSON.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    disciplinas = dados["disciplinas"]

    if not disciplinas:
        raise ValueError("O JSON não possui disciplinas para pesquisar.")

    # Usa dados reais do currículo para montar as buscas.
    codigo_teste = disciplinas[0]["codigo"]
    nome_teste = disciplinas[0]["nome"]
    palavra_teste = nome_teste.split()[0]

    buscas = [
        ("busca_por_codigo", codigo_teste),
        ("busca_por_nome", palavra_teste),
    ]

    resultados_benchmark = []

    print("Conectando aos bancos...")

    # As conexões ficam abertas durante as medições.
    with psycopg.connect(DATABASE_URL) as postgres:
        with MongoClient(MONGO_URI) as cliente_mongo:
            colecao = cliente_mongo["tads_curricular"]["cursos"]

            driver_neo4j = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
            )

            try:
                driver_neo4j.verify_connectivity()

                with driver_neo4j.session() as sessao:
                    bancos = [
                        (
                            "PostgreSQL",
                            lambda busca: consultar_postgres(
                                postgres, busca
                            ),
                        ),
                        (
                            "MongoDB",
                            lambda busca: consultar_mongodb(
                                colecao, busca
                            ),
                        ),
                        (
                            "Neo4j",
                            lambda busca: consultar_neo4j(
                                sessao, busca
                            ),
                        ),
                    ]

                    for tipo_busca, busca in buscas:
                        print(f"\nTeste: {tipo_busca} — {busca}")

                        for nome_banco, funcao in bancos:
                            resultado = medir(
                                nome_banco, funcao, busca
                            )
                            resultado["tipo_busca"] = tipo_busca
                            resultados_benchmark.append(resultado)

                            print(
                                f"{nome_banco}: "
                                f"{resultado['media_ms']} ms "
                                f"(média), "
                                f"{resultado['resultados']} resultado(s)"
                            )
            finally:
                driver_neo4j.close()

    # Salva os dados para a análise do trabalho.
    campos = [
        "tipo_busca",
        "banco",
        "busca",
        "resultados",
        "repeticoes",
        "media_ms",
        "mediana_ms",
        "minimo_ms",
        "maximo_ms",
    ]

    with ARQUIVO_RESULTADOS.open(
        "w", newline="", encoding="utf-8-sig"
    ) as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(resultados_benchmark)

    print(f"\nBenchmark concluído: {ARQUIVO_RESULTADOS}")
    print("Confira os tempos e a quantidade de resultados de cada banco.")


if __name__ == "__main__":
    main()
