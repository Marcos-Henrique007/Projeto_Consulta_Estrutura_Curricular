
# Modelos Lógicos dos Bancos de Dados

Este documento apresenta os modelos lógicos utilizados no projeto de consulta à estrutura curricular, considerando os bancos de dados relacional, não relacional orientado a documentos e não relacional orientado a grafos.

## 1. Modelo Relacional

### Entidade Curso

- `id`: identificador do curso (chave primária).
- `nome`: nome do curso.
- `instituicao`: instituição de ensino.

### Entidade Disciplinas

- `id`: identificador da disciplina (chave primária).
- `codigo`: código da disciplina.
- `nome`: nome da disciplina.
- `carga_horaria`: carga horária da disciplina.
- `curso_id`: identificador do curso ao qual a disciplina pertence (chave estrangeira).

### Tabela pre_requisitos

- `disciplina_id`: identificador da disciplina que possui um pré-requisito (chave estrangeira).
- `requisito_id`: identificador da disciplina exigida como pré-requisito (chave estrangeira).
- Chave primária composta por `disciplina_id` e `requisito_id`.

### Relacionamentos

- Um curso pode possuir várias disciplinas.
- Cada disciplina pertence a um curso.
- Uma disciplina pode possuir vários pré-requisitos.
- Uma disciplina pode ser pré-requisito de várias outras disciplinas.
- A tabela `pre_requisitos` representa o relacionamento muitos-para-muitos entre disciplinas.

### Diagrama relacional

![Modelo lógico relacional](banco_relacional/modelo_projeto_ciencia_de_dados.png)

---

## 2. Modelo Não Relacional Orientado a Documentos (MongoDB)

### Estrutura proposta

O modelo documental utiliza uma coleção chamada `cursos`. Cada documento representa um curso e contém seus dados gerais e um array de documentos de disciplinas embutidos.

### Coleção `cursos`

| Campo | Tipo | Descrição |
|---|---|---|
| `_id` | ObjectId | Identificador único do curso |
| `nome` | String | Nome do curso |
| `instituicao` | String | Instituição de ensino |
| `disciplinas` | Array de documentos | Disciplinas do currículo |

### Campos de cada disciplina embutida

| Campo | Tipo | Descrição |
|---|---|---|
| `codigo` | String | Código da disciplina |
| `nome` | String | Nome da disciplina |
| `carga_horaria` | Number | Carga horária da disciplina |
| `pre_requisitos` | Array de String | Códigos das disciplinas exigidas como pré-requisito |

### Exemplo de documento

O exemplo abaixo é ilustrativo e não representa necessariamente os dados reais da grade curricular.

```json
{
  "_id": {
    "$oid": "671000000000000000000001"
  },
  "nome": "Tecnologia em Análise e Desenvolvimento de Sistemas",
  "instituicao": "UFRN",
  "disciplinas": [
    {
      "codigo": "DISC001",
      "nome": "Introdução à Programação",
      "carga_horaria": 60,
      "pre_requisitos": []
    },
    {
      "codigo": "DISC002",
      "nome": "Programação Avançada",
      "carga_horaria": 60,
      "pre_requisitos": ["DISC001"]
    }
  ]
}
```

### Justificativa

As disciplinas foram embutidas no documento do curso porque a aplicação precisa consultar e apresentar a estrutura curricular de forma conjunta. Essa organização permite recuperar os dados do curso e suas disciplinas em uma única consulta.

Os pré-requisitos são representados por uma lista de códigos, evitando a necessidade de uma coleção exclusiva para esse relacionamento.

O modelo considera um currículo por curso, sem armazenar versões históricas. A aplicação deverá validar os códigos dos pré-requisitos, pois o MongoDB não garante automaticamente que eles correspondam a disciplinas existentes.

### Diagrama documental

![Modelo lógico documental](banco_nao_relacional_arquivos/Diagrama_banco_nao_relacional_documento.png)

---

## 3. Modelo Não Relacional Orientado a Grafos

Esta seção será preenchida após a definição do modelo lógico orientado a grafos.

### Nós e propriedades

A definir.

### Relacionamentos

A definir.

### Diagrama de grafos

**Inserir aqui a imagem do modelo lógico orientado a grafos.**

### Justificativa

A definir após a construção do modelo lógico de grafos.

---

## 4. Comparação dos Modelos

| Abordagem | Organização dos dados | Representação dos pré-requisitos |
|---|---|---|
| Relacional | Tabelas relacionadas por chaves | Tabela associativa |
| Documental (MongoDB) | Curso com disciplinas embutidas | Array de códigos |
| Orientada a grafos | A definir | A definir |
