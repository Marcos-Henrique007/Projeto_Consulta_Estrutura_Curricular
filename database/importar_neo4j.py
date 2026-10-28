import json
import os
from pathlib import Path

from neo4j import GraphDatabase


# Caminho do arquivo curriculo.json
BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_CURRICULO = BASE_DIR / "curriculo.json"


# Carrega os dados do currículo
with open(ARQUIVO_CURRICULO, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

curso = dados["curso"]
disciplinas = dados["disciplinas"]


# Configurações de conexão com o Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "tads_dev_123")


# Confere se os códigos das disciplinas são únicos
codigos = [disciplina["codigo"] for disciplina in disciplinas]

if len(codigos) != len(set(codigos)):
    raise ValueError("Existem códigos de disciplinas duplicados no JSON.")


# Confere se todos os pré-requisitos existem no currículo
codigos_validos = set(codigos)

for disciplina in disciplinas:
    for tipo in (
        "pre_requisitos",
        "pre_requisitos_alternativos"
    ):
        for requisito in disciplina.get(tipo, []):
            if requisito not in codigos_validos:
                raise ValueError(
                    f"O pré-requisito {requisito}, informado para "
                    f"{disciplina['codigo']}, não foi encontrado "
                    "no curriculo.json."
                )


def importar_curriculo(tx, curso, disciplinas):
    # Remove as disciplinas antigas e seus relacionamentos.
    tx.run("""
        MATCH (d:Disciplina)
        DETACH DELETE d
    """).consume()

    # Cria ou atualiza o nó do curso.
    tx.run("""
        MERGE (c:Curso {nome: $nome})
        SET c.instituicao = $instituicao
    """,
        nome=curso["nome"],
        instituicao=curso.get("instituicao", "")
    ).consume()

    # Cria as disciplinas e relaciona cada uma ao curso.
    tx.run("""
        MATCH (c:Curso {nome: $nome})
        UNWIND $disciplinas AS item

        CREATE (d:Disciplina {
            codigo: item.codigo,
            nome: item.nome,
            creditos: item.creditos
        })

        MERGE (c)-[:OFERECE]->(d)
    """,
        nome=curso["nome"],
        disciplinas=disciplinas
    ).consume()

    # Cria os relacionamentos dos pré-requisitos obrigatórios.
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

    # Cria os relacionamentos dos pré-requisitos alternativos.
    # Basta cumprir um dos requisitos alternativos para atender à regra.
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


# Conecta ao Neo4j e importa os dados.
driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

try:
    driver.verify_connectivity()

    with driver.session() as sessao:
        sessao.execute_write(
            importar_curriculo,
            curso,
            disciplinas
        )

    print(
        "Importação concluída com sucesso!\n"
        f"Curso: {curso['nome']}\n"
        f"Disciplinas importadas: {len(disciplinas)}"
    )

finally:
    driver.close()
    import json
import os
from pathlib import Path

from neo4j import GraphDatabase


# Caminho do arquivo curriculo.json
BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_CURRICULO = BASE_DIR / "curriculo.json"


# Carrega os dados do currículo
with open(ARQUIVO_CURRICULO, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

curso = dados["curso"]
disciplinas = dados["disciplinas"]


# Configurações de conexão com o Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "tads_dev_123")


# Confere se os códigos das disciplinas são únicos
codigos = [disciplina["codigo"] for disciplina in disciplinas]

if len(codigos) != len(set(codigos)):
    raise ValueError("Existem códigos de disciplinas duplicados no JSON.")


# Confere se todos os pré-requisitos existem no currículo
codigos_validos = set(codigos)

for disciplina in disciplinas:
    for tipo in (
        "pre_requisitos",
        "pre_requisitos_alternativos"
    ):
        for requisito in disciplina.get(tipo, []):
            if requisito not in codigos_validos:
                raise ValueError(
                    f"O pré-requisito {requisito}, informado para "
                    f"{disciplina['codigo']}, não foi encontrado "
                    "no curriculo.json."
                )


def importar_curriculo(tx, curso, disciplinas):
    # Remove as disciplinas antigas e seus relacionamentos.
    tx.run("""
        MATCH (d:Disciplina)
        DETACH DELETE d
    """).consume()

    # Cria ou atualiza o nó do curso.
    tx.run("""
        MERGE (c:Curso {nome: $nome})
        SET c.instituicao = $instituicao
    """,
        nome=curso["nome"],
        instituicao=curso.get("instituicao", "")
    ).consume()

    # Cria as disciplinas e relaciona cada uma ao curso.
    tx.run("""
        MATCH (c:Curso {nome: $nome})
        UNWIND $disciplinas AS item

        CREATE (d:Disciplina {
            codigo: item.codigo,
            nome: item.nome,
            creditos: item.creditos
        })

        MERGE (c)-[:OFERECE]->(d)
    """,
        nome=curso["nome"],
        disciplinas=disciplinas
    ).consume()

    # Cria os relacionamentos dos pré-requisitos obrigatórios.
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

    # Cria os relacionamentos dos pré-requisitos alternativos.
    # Basta cumprir um dos requisitos alternativos para atender à regra.
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


# Conecta ao Neo4j e importa os dados.
driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

try:
    driver.verify_connectivity()

    with driver.session() as sessao:
        sessao.execute_write(
            importar_curriculo,
            curso,
            disciplinas
        )

    print(
        "Importação concluída com sucesso!\n"
        f"Curso: {curso['nome']}\n"
        f"Disciplinas importadas: {len(disciplinas)}"
    )

finally:
    driver.close()