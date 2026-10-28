import json
import os
from pathlib import Path
from neo4j import GraphDatabase

BASE_DIR = Path(__file__).resolve().parent
with open(BASE_DIR / "curriculo.json", encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USUARIO = os.getenv("NEO4J_USER", "neo4j")
SENHA = os.getenv("NEO4J_PASSWORD", "tads_dev_123")

driver = GraphDatabase.driver(URI, auth=(USUARIO, SENHA))
driver.verify_connectivity()

with driver.session() as sessao:
    sessao.run("""
        MERGE (c:Curso {nome: $nome, ano: $ano})
        SET c.instituicao = $instituicao
    """, nome=dados["curso"]["nome"], ano=dados["curso"]["ano"],
         instituicao=dados["curso"]["instituicao"])

    # Remove apenas as disciplinas deste currículo antes de recriá-las.
    sessao.run("""
        MATCH (c:Curso {nome: $nome, ano: $ano})-[:OFERECE]->(d:Disciplina)
        DETACH DELETE d
    """, nome=dados["curso"]["nome"], ano=dados["curso"]["ano"])

    for d in dados["disciplinas"]:
        sessao.run("""
            MATCH (c:Curso {nome: $curso_nome, ano: $ano})
            MERGE (disc:Disciplina {codigo: $codigo})
            SET disc.nome = $nome, disc.creditos = $creditos
            MERGE (c)-[:OFERECE]->(disc)
        """, curso_nome=dados["curso"]["nome"], ano=dados["curso"]["ano"],
             codigo=d["codigo"], nome=d["nome"], creditos=d["creditos"])

    for d in dados["disciplinas"]:
        for requisito in d.get("pre_requisitos", []):
            sessao.run("""
                MATCH (disc:Disciplina {codigo: $codigo})
                MATCH (req:Disciplina {codigo: $requisito})
                MERGE (req)-[:PRE_REQUISITO_DE]->(disc)
            """, codigo=d["codigo"], requisito=requisito)

driver.close()
print(f"Importação concluída: {len(dados['disciplinas'])} disciplinas no Neo4j.")
