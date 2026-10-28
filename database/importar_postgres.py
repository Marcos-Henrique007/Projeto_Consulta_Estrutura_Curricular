import json
import os
from pathlib import Path

import psycopg

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "curriculo.json", encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

conninfo = os.getenv(
    "DATABASE_URL",
    "host=localhost port=5432 dbname=tads user=tads password=tads_dev"
)

with psycopg.connect(conninfo) as conn:
    with conn.cursor() as cur:
        curso = dados["curso"]

        # Garante a existência da tabela de requisitos alternativos.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pre_requisitos_alternativos (
                disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id),
                requisito_id INTEGER NOT NULL REFERENCES disciplinas(id),
                PRIMARY KEY (disciplina_id, requisito_id),
                CHECK (disciplina_id <> requisito_id)
            )
        """)

        cur.execute("""
            INSERT INTO cursos (nome, instituicao)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (curso["nome"], curso["instituicao"]))

        cur.execute(
            "SELECT id FROM cursos WHERE nome = %s",
            (curso["nome"],)
        )

        curso_id = cur.fetchone()[0]

        codigos = [d["codigo"] for d in dados["disciplinas"]]

        # Remove os relacionamentos antigos destas disciplinas.
        cur.execute("""
            DELETE FROM pre_requisitos
            WHERE disciplina_id IN (
                SELECT id FROM disciplinas
                WHERE codigo = ANY(%s)
            )
            OR requisito_id IN (
                SELECT id FROM disciplinas
                WHERE codigo = ANY(%s)
            )
        """, (codigos, codigos))

        cur.execute("""
            DELETE FROM pre_requisitos_alternativos
            WHERE disciplina_id IN (
                SELECT id FROM disciplinas
                WHERE codigo = ANY(%s)
            )
            OR requisito_id IN (
                SELECT id FROM disciplinas
                WHERE codigo = ANY(%s)
            )
        """, (codigos, codigos))

        ids_por_codigo = {}

        # Cadastra ou atualiza as disciplinas.
        for disciplina in dados["disciplinas"]:
            cur.execute("""
                INSERT INTO disciplinas (
                    codigo, nome, creditos, curso_id
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome,
                    creditos = EXCLUDED.creditos,
                    curso_id = EXCLUDED.curso_id
                RETURNING id
            """, (
                disciplina["codigo"],
                disciplina["nome"],
                disciplina["creditos"],
                curso_id
            ))

            ids_por_codigo[disciplina["codigo"]] = cur.fetchone()[0]

        # Insere os pré-requisitos obrigatórios.
        for disciplina in dados["disciplinas"]:
            for requisito_codigo in disciplina.get(
                "pre_requisitos", []
            ):
                if requisito_codigo not in ids_por_codigo:
                    raise ValueError(
                        f"Pré-requisito {requisito_codigo} "
                        "não encontrado no JSON."
                    )

                cur.execute("""
                    INSERT INTO pre_requisitos (
                        disciplina_id, requisito_id
                    )
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    ids_por_codigo[disciplina["codigo"]],
                    ids_por_codigo[requisito_codigo]
                ))

        # Insere os pré-requisitos alternativos.
        for disciplina in dados["disciplinas"]:
            for requisito_codigo in disciplina.get(
                "pre_requisitos_alternativos", []
            ):
                if requisito_codigo not in ids_por_codigo:
                    raise ValueError(
                        f"Pré-requisito alternativo "
                        f"{requisito_codigo} não encontrado no JSON."
                    )

                cur.execute("""
                    INSERT INTO pre_requisitos_alternativos (
                        disciplina_id, requisito_id
                    )
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    ids_por_codigo[disciplina["codigo"]],
                    ids_por_codigo[requisito_codigo]
                ))

print(
    "Importação concluída: "
    f"{len(dados['disciplinas'])} disciplinas no PostgreSQL."
)