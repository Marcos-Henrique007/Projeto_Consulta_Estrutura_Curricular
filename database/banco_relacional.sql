CREATE TABLE IF NOT EXISTS cursos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    instituicao VARCHAR(150) NOT NULL
);

CREATE TABLE IF NOT EXISTS disciplinas (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    nome VARCHAR(200) NOT NULL,
    creditos INTEGER NOT NULL CHECK (creditos > 0),
    curso_id INTEGER NOT NULL REFERENCES cursos(id)
);

-- Compatibilidade com o esquema antigo.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'disciplinas'
          AND column_name = 'carga_horaria'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'disciplinas'
          AND column_name = 'creditos'
    ) THEN
        ALTER TABLE disciplinas
        RENAME COLUMN carga_horaria TO creditos;
    END IF;
END $$;

-- Pré-requisitos obrigatórios.
CREATE TABLE IF NOT EXISTS pre_requisitos (
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id),
    requisito_id INTEGER NOT NULL REFERENCES disciplinas(id),
    PRIMARY KEY (disciplina_id, requisito_id),
    CHECK (disciplina_id <> requisito_id)
);

-- Pré-requisitos alternativos: basta cumprir um deles.
CREATE TABLE IF NOT EXISTS pre_requisitos_alternativos (
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id),
    requisito_id INTEGER NOT NULL REFERENCES disciplinas(id),
    PRIMARY KEY (disciplina_id, requisito_id),
    CHECK (disciplina_id <> requisito_id)
);

CREATE INDEX IF NOT EXISTS idx_disciplinas_nome
    ON disciplinas(nome);

CREATE INDEX IF NOT EXISTS idx_pre_requisitos_requisito
    ON pre_requisitos(requisito_id);

CREATE INDEX IF NOT EXISTS idx_pre_requisitos_alternativos_requisito
    ON pre_requisitos_alternativos(requisito_id);