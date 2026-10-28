from flask import Flask, render_template, request, jsonify
from time import perf_counter

import psycopg
from psycopg.rows import dict_row
from pymongo import MongoClient
from neo4j import GraphDatabase

app = Flask(__name__)

# Conexões dos bancos locais
MONGO = MongoClient("mongodb://localhost:27017")
COLECAO = MONGO["tads_curricular"]["cursos"]

NEO4J = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "tads_dev_123")
)

POSTGRES = (
    "host=localhost port=5432 dbname=tads "
    "user=tads password=tads_dev"
)


@app.route("/")
def index():
    return render_template("index.html")


def consultar_postgres(busca):
    with psycopg.connect(POSTGRES, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.codigo,
                    d.nome,
                    d.creditos,
                    COALESCE(
                        array_agg(r.codigo)
                        FILTER (WHERE r.codigo IS NOT NULL),
                        ARRAY[]::varchar[]
                    ) AS pre_requisitos
                FROM disciplinas d
                LEFT JOIN pre_requisitos p
                    ON p.disciplina_id = d.id
                LEFT JOIN disciplinas r
                    ON r.id = p.requisito_id
                WHERE d.codigo ILIKE %s OR d.nome ILIKE %s
                GROUP BY d.id
                ORDER BY d.codigo
                LIMIT 50
                """,
                (f"%{busca}%", f"%{busca}%")
            )
            return [dict(row) for row in cur.fetchall()]


def consultar_mongodb(busca):
    documento = COLECAO.find_one(
        {"disciplinas": {"$elemMatch": {
            "$or": [
                {"codigo": {"$regex": busca, "$options": "i"}},
                {"nome": {"$regex": busca, "$options": "i"}}
            ]
        }}},
        {"disciplinas": 1, "_id": 0}
    )

    if not documento:
        return []

    return [
        {
            "codigo": d["codigo"],
            "nome": d["nome"],
            "creditos": d["creditos"],
            "pre_requisitos": d.get("pre_requisitos", [])
        }
        for d in documento["disciplinas"]
        if busca.lower() in d["codigo"].lower()
        or busca.lower() in d["nome"].lower()
    ][:50]


def consultar_neo4j(busca):
    with NEO4J.session() as sessao:
        resultado = sessao.run(
            """
            MATCH (d:Disciplina)
            WHERE toLower(d.codigo) CONTAINS toLower($busca)
               OR toLower(d.nome) CONTAINS toLower($busca)
            OPTIONAL MATCH (r:Disciplina)-[:PRE_REQUISITO_DE]->(d)
            RETURN d.codigo AS codigo,
                   d.nome AS nome,
                   d.creditos AS creditos,
                   collect(DISTINCT r.codigo) AS pre_requisitos
            ORDER BY codigo
            LIMIT 50
            """,
            busca=busca
        )
        return [record.data() for record in resultado]


@app.route("/api/consultar", methods=["POST"])
def consultar():
    dados = request.get_json(silent=True) or {}
    banco = dados.get("banco", "")
    busca = dados.get("busca", "").strip()

    if banco not in ("relacional", "documental", "grafo"):
        return jsonify({"erro": "Selecione um banco válido."}), 400

    if not busca:
        return jsonify({"erro": "Digite um código ou nome de disciplina."}), 400

    try:
        inicio = perf_counter()

        if banco == "relacional":
            resultados = consultar_postgres(busca)
        elif banco == "documental":
            resultados = consultar_mongodb(busca)
        else:
            resultados = consultar_neo4j(busca)

        tempo_ms = (perf_counter() - inicio) * 1000

        return jsonify({
            "banco": banco,
            "quantidade": len(resultados),
            "tempo_ms": round(tempo_ms, 3),
            "resultados": resultados
        })

    except Exception as erro:
        app.logger.exception("Erro ao consultar o banco")
        return jsonify({
            "erro": f"Não foi possível consultar o banco: {erro}"
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
