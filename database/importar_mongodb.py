import json
from pathlib import Path
from pymongo import MongoClient

BASE_DIR = Path(__file__).resolve().parent
with open(BASE_DIR / "curriculo.json", encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

cliente = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
db = cliente["tads_curricular"]
colecao = db["cursos"]

documento = {
    "nome": dados["curso"]["nome"],
    "instituicao": dados["curso"]["instituicao"],
    "ano": dados["curso"]["ano"],
    "disciplinas": dados["disciplinas"]
}

colecao.replace_one({"nome": documento["nome"], "ano": documento["ano"]},
                    documento, upsert=True)
print(f"Importação concluída: {len(dados['disciplinas'])} disciplinas embutidas no MongoDB.")
cliente.close()
