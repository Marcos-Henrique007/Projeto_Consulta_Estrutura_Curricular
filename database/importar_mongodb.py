import json
import os
from pathlib import Path

from pymongo import MongoClient

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_CURRICULO = BASE_DIR / "curriculo.json"

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


def importar_curriculo():
    # Lê o currículo salvo no arquivo JSON.
    with open(ARQUIVO_CURRICULO, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    curso = dados["curso"]
    disciplinas = dados["disciplinas"]

    # Mantém o mesmo formato de documento usado pelo Flask.
    documento = {
        "curso": {
            "nome": curso["nome"],
            "instituicao": curso["instituicao"],
        },
        "disciplinas": disciplinas,
    }

    # Atualiza o documento do curso ou cria um se ainda não existir.
    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) as cliente:
        colecao = cliente["tads_curricular"]["cursos"]

        colecao.replace_one(
            {"curso.nome": documento["curso"]["nome"]},
            documento,
            upsert=True,
        )

    print(
        "Importação concluída: "
        f"{len(disciplinas)} disciplina(s) no MongoDB."
    )


if __name__ == "__main__":
    importar_curriculo()
