import json
import os
from pathlib import Path

from neo4j import GraphDatabase

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_CURRICULO = BASE_DIR / "curriculo.json"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "tads_dev_123")


def importar_curriculo(tx, curso, disciplinas):
    nome_curso = curso["nome"]

    # Remove apenas as disciplinas pertencentes a este curso.
    tx.run("""
        MATCH (c:Curso {nome: $nome})-[:OFERECE]->(d:Disciplina)
        DETACH DELETE d
    """, nome=nome_curso).consume()

    # Cria ou atualiza o curso.
    tx.run("""
        MERGE (c:Curso {nome: $nome})
        SET c.instituicao = $instituicao
    """,
        nome=nome_curso,
        instituicao=curso.get("instituicao", "")
    ).consume()

    # Cria as disciplinas e vincula ao curso.
    tx.run("""
        MATCH (c:Curso {nome: $nome})
        UNWIND $disciplinas AS item
        MERGE (d:Disciplina {codigo: item.codigo})
        SET d.nome = item.nome,
            d.creditos = item.creditos
        MERGE (c)-[:OFERECE]->(d)
    """,
        nome=nome_curso,
        disciplinas=disciplinas
    ).consume()

    # Cria os pré-requisitos obrigatórios.
    for disciplina in disciplinas:
        for requisito in disciplina.get("pre_requisitos", []):
            tx.run("""
                MATCH (disc:Disciplina {codigo: $codigo})
                MATCH (req:Disciplina {codigo: $requisito})
                MERGE (req)-[:PRE_REQUISITO_DE]->(disc)
            """,
                codigo=disciplina["codigo"],
                requisito=requisito
            ).consume()

    # Cria os pré-requisitos alternativos.
    for disciplina in disciplinas:
        for requisito in disciplina.get(
            "pre_requisitos_alternativos", []
        ):
            tx.run("""
                MATCH (disc:Disciplina {codigo: $codigo})
                MATCH (req:Disciplina {codigo: $requisito})
                MERGE (req)-[:PRE_REQUISITO_ALTERNATIVO_DE]->(disc)
            """,
                codigo=disciplina["codigo"],
                requisito=requisito
            ).consume()


def main():
    with ARQUIVO_CURRICULO.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    curso = dados["curso"]
    disciplinas = dados["disciplinas"]

    codigos = [d["codigo"] for d in disciplinas]

    if len(codigos) != len(set(codigos)):
        raise ValueError("Existem códigos de disciplinas duplicados.")

    codigos_validos = set(codigos)

    for disciplina in disciplinas:
        for tipo in (
            "pre_requisitos",
            "pre_requisitos_alternativos"
        ):
            for requisito in disciplina.get(tipo, []):
                if requisito not in codigos_validos:
                    raise ValueError(
                        f"Pré-requisito {requisito} não encontrado "
                        f"para a disciplina {disciplina['codigo']}."
                    )

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    try:
        driver.verify_connectivity()

        with driver.session() as sessao:
            sessao.execute_write(
                importar_curriculo, curso, disciplinas
            )

        print(
            "Importação concluída!\n"
            f"Curso: {curso['nome']}\n"
            f"Disciplinas: {len(disciplinas)}"
        )
    finally:
        driver.close()


if __name__ == "__main__":
    main()
