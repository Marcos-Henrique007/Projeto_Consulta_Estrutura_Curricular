CREATE TABLE IF NOT EXISTS cursos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    instituicao VARCHAR(150) NOT NULL
);

CREATE TABLE IF NOT EXISTS disciplinas (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    nome VARCHAR(200) NOT NULL,
    carga_horaria INTEGER NOT NULL CHECK (carga_horaria > 0),
    curso_id INTEGER NOT NULL REFERENCES cursos(id)
);

CREATE TABLE IF NOT EXISTS pre_requisitos (
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id),
    requisito_id INTEGER NOT NULL REFERENCES disciplinas(id),
    PRIMARY KEY (disciplina_id, requisito_id),
    CHECK (disciplina_id <> requisito_id)
);

CREATE INDEX IF NOT EXISTS idx_disciplinas_nome
    ON disciplinas(nome);

CREATE INDEX IF NOT EXISTS idx_pre_requisitos_requisito
    ON pre_requisitos(requisito_id);
