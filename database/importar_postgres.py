
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

        cur.execute(
            """
            INSERT INTO cursos (nome, instituicao)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (curso["nome"], curso["instituicao"])
        )

        cur.execute(
            "SELECT id FROM cursos WHERE nome = %s",
            (curso["nome"],)
        )
        curso_id = cur.fetchone()[0]

        codigos = [d["codigo"] for d in dados["disciplinas"]]

        # Remove os relacionamentos das disciplinas que serão atualizadas.
        cur.execute(
            """
            DELETE FROM pre_requisitos
            WHERE disciplina_id IN (
                SELECT id FROM disciplinas WHERE codigo = ANY(%s)
            )
            OR requisito_id IN (
                SELECT id FROM disciplinas WHERE codigo = ANY(%s)
            )
            """,
            (codigos, codigos)
        )

        # Atualiza disciplinas existentes ou cadastra as novas.
        ids_por_codigo = {}

        for disciplina in dados["disciplinas"]:
            cur.execute(
                """
                INSERT INTO disciplinas (codigo, nome, creditos, curso_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome,
                    creditos = EXCLUDED.creditos,
                    curso_id = EXCLUDED.curso_id
                RETURNING id
                """,
                (
                    disciplina["codigo"],
                    disciplina["nome"],
                    disciplina["creditos"],
                    curso_id
                )
            )

            ids_por_codigo[disciplina["codigo"]] = cur.fetchone()[0]

        # Recria somente os pré-requisitos informados no JSON.
        for disciplina in dados["disciplinas"]:
            for requisito_codigo in disciplina.get("pre_requisitos", []):
                if requisito_codigo not in ids_por_codigo:
                    raise ValueError(
                        f"Pré-requisito {requisito_codigo} "
                        "não encontrado no JSON."
                    )

                cur.execute(
                    """
                    INSERT INTO pre_requisitos
                        (disciplina_id, requisito_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        ids_por_codigo[disciplina["codigo"]],
                        ids_por_codigo[requisito_codigo]
                    )
                )

print(
    f"Importação concluída: "
    f"{len(dados['disciplinas'])} disciplinas no PostgreSQL."
)
