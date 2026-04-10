# Especificação Técnica de Saída de Prompt JSONL

## Visão Geral

Esta especificação descreve a implementação do formato de saída JSONL (JSON Lines)
para respostas de prompt no TrustGraph. JSONL permite a extração de dados estruturados
de forma resiliente à truncagem das respostas de LLM, abordando problemas críticos
relacionados à corrupção de saídas de matriz JSON quando as respostas de LLM atingem
os limites de tokens de saída.

Esta implementação suporta os seguintes casos de uso:

1. **Extração Resistente à Truncagem**: Extrair resultados parciais válidos mesmo quando
   a saída do LLM é truncada no meio da resposta.
2. **Extração em Larga Escala**: Lidar com a extração de muitos itens sem risco de
   falha completa devido a limites de tokens.
3. **Extração de Tipos Mistos**: Suportar a extração de vários tipos de entidades
   (definições, relacionamentos, entidades, atributos) em um único prompt.
4. **Saída Compatível com Streaming**: Permitir o processamento futuro de streaming/incremental
   dos resultados da extração.

## Objetivos

**Compatibilidade com versões anteriores**: As instruções existentes que usam `response-type: "text"` e
  `response-type: "json"` continuam a funcionar sem modificação.
**Resiliência à truncagem**: Saídas parciais do LLM produzem resultados válidos parciais
  em vez de falha completa.
**Validação de esquema**: Suporte à validação de esquema JSON para objetos individuais.
**Uniões discriminadas**: Suporte a saídas de tipos mistos usando um campo `type`
  discriminador.
**Alterações mínimas na API**: Estenda a configuração de instruções existente com um novo
  tipo de resposta e chave de esquema.

## Contexto

### Arquitetura atual

O serviço de instruções suporta dois tipos de resposta:

1. `response-type: "text"` - Resposta de texto bruto retornada como está.
2. `response-type: "json"` - JSON analisado da resposta, validado contra
   um `schema` opcional.

Implementação atual em `trustgraph-flow/trustgraph/template/prompt_manager.py`:

```python
class Prompt:
    def __init__(self, template, response_type = "text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema
```

### Limitações Atuais

Quando os prompts de extração solicitam a saída como arrays JSON (`[{...}, {...}, ...]`):

**Corrupção por truncamento**: Se o LLM atinge os limites de tokens de saída no meio do array, a
  resposta inteira se torna JSON inválido e não pode ser analisada.
**Análise "tudo ou nada"**: É necessário receber a saída completa antes de analisar.
**Sem resultados parciais**: Uma resposta truncada produz zero dados utilizáveis.
**Não confiável para grandes extrações**: Quanto mais itens extraídos, maior o risco de falha.

Esta especificação aborda essas limitações introduzindo o formato JSONL para
prompts de extração, onde cada item extraído é um objeto JSON completo em sua
própria linha.

## Design Técnico

### Extensão do Tipo de Resposta

Adicione um novo tipo de resposta `"jsonl"`, juntamente com os tipos existentes `"text"` e `"json"`.

#### Alterações de Configuração

**Novo valor do tipo de resposta:**

```
"response-type": "jsonl"
```

**Interpretação do esquema:**

A chave existente `"schema"` é usada tanto para o tipo de resposta `"json"` quanto para o tipo de resposta `"jsonl"`.
A interpretação depende do tipo de resposta:

`"json"`: O esquema descreve toda a resposta (geralmente um array ou objeto).
`"jsonl"`: O esquema descreve cada linha/objeto individual.

```json
{
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": { "type": "string" },
      "definition": { "type": "string" }
    },
    "required": ["entity", "definition"]
  }
}
```

Isso evita alterações nas ferramentas de configuração e nos editores.

### Especificação do Formato JSONL

#### Extração Simples

Para prompts que extraem um único tipo de objeto (definições, relacionamentos,
tópicos, linhas), a saída é um objeto JSON por linha, sem wrapper:

**Formato de saída do prompt:**
```
{"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"}
{"entity": "chlorophyll", "definition": "Green pigment in plants"}
{"entity": "mitochondria", "definition": "Powerhouse of the cell"}
```

**Contraste com o formato anterior de array JSON:**
```json
[
  {"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"},
  {"entity": "chlorophyll", "definition": "Green pigment in plants"},
  {"entity": "mitochondria", "definition": "Powerhouse of the cell"}
]
```

Se o LLM truncar após a linha 2, o formato de array JSON resulta em JSON inválido,
enquanto o JSONL produz dois objetos válidos.

#### Extração de Tipos Mistos (Uniões Discriminadas)

Para prompts que extraem vários tipos de objetos (por exemplo, definições e
relacionamentos, ou entidades, relacionamentos e atributos), use um campo `"type"`
como discriminador:

**Formato de saída do prompt:**
```
{"type": "definition", "entity": "DNA", "definition": "Molecule carrying genetic instructions"}
{"type": "relationship", "subject": "DNA", "predicate": "located_in", "object": "cell nucleus", "object-entity": true}
{"type": "definition", "entity": "RNA", "definition": "Molecule that carries genetic information"}
{"type": "relationship", "subject": "RNA", "predicate": "transcribed_from", "object": "DNA", "object-entity": true}
```

**Esquema para uniões discriminadas usa `oneOf`:**
```json
{
  "response-type": "jsonl",
  "schema": {
    "oneOf": [
      {
        "type": "object",
        "properties": {
          "type": { "const": "definition" },
          "entity": { "type": "string" },
          "definition": { "type": "string" }
        },
        "required": ["type", "entity", "definition"]
      },
      {
        "type": "object",
        "properties": {
          "type": { "const": "relationship" },
          "subject": { "type": "string" },
          "predicate": { "type": "string" },
          "object": { "type": "string" },
          "object-entity": { "type": "boolean" }
        },
        "required": ["type", "subject", "predicate", "object", "object-entity"]
      }
    ]
  }
}
```

#### Extração de Ontologia

Para extração baseada em ontologia com entidades, relacionamentos e atributos:

**Formato de saída do prompt:**
```
{"type": "entity", "entity": "Cornish pasty", "entity_type": "fo/Recipe"}
{"type": "entity", "entity": "beef", "entity_type": "fo/Food"}
{"type": "relationship", "subject": "Cornish pasty", "subject_type": "fo/Recipe", "relation": "fo/has_ingredient", "object": "beef", "object_type": "fo/Food"}
{"type": "attribute", "entity": "Cornish pasty", "entity_type": "fo/Recipe", "attribute": "fo/serves", "value": "4 people"}
```

### Detalhes de Implementação

#### Classe Prompt

A classe `Prompt` existente não requer alterações. O campo `schema` é reutilizado
para JSONL, com sua interpretação determinada por `response_type`:

```python
class Prompt:
    def __init__(self, template, response_type="text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema  # Interpretation depends on response_type
```

#### PromptManager.load_config

Nenhuma alteração necessária - o carregamento da configuração existente já lida com a
`schema` chave.

#### Análise de JSONL

Adicionar um novo método de análise para respostas JSONL:

```python
def parse_jsonl(self, text):
    """
    Parse JSONL response, returning list of valid objects.

    Invalid lines (malformed JSON, empty lines) are skipped with warnings.
    This provides truncation resilience - partial output yields partial results.
    """
    results = []

    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip markdown code fence markers if present
        if line.startswith('```'):
            continue

        try:
            obj = json.loads(line)
            results.append(obj)
        except json.JSONDecodeError as e:
            # Log warning but continue - this provides truncation resilience
            logger.warning(f"JSONL parse error on line {line_num}: {e}")

    return results
```

#### Alterações no PromptManager.invoke

Estenda o método invoke para lidar com o novo tipo de resposta:

```python
async def invoke(self, id, input, llm):
    logger.debug("Invoking prompt template...")

    terms = self.terms | self.prompts[id].terms | input
    resp_type = self.prompts[id].response_type

    prompt = {
        "system": self.system_template.render(terms),
        "prompt": self.render(id, input)
    }

    resp = await llm(**prompt)

    if resp_type == "text":
        return resp

    if resp_type == "json":
        try:
            obj = self.parse_json(resp)
        except:
            logger.error(f"JSON parse failed: {resp}")
            raise RuntimeError("JSON parse fail")

        if self.prompts[id].schema:
            try:
                validate(instance=obj, schema=self.prompts[id].schema)
                logger.debug("Schema validation successful")
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

    if resp_type == "jsonl":
        objects = self.parse_jsonl(resp)

        if not objects:
            logger.warning("JSONL parse returned no valid objects")
            return []

        # Validate each object against schema if provided
        if self.prompts[id].schema:
            validated = []
            for i, obj in enumerate(objects):
                try:
                    validate(instance=obj, schema=self.prompts[id].schema)
                    validated.append(obj)
                except Exception as e:
                    logger.warning(f"Object {i} failed schema validation: {e}")
            return validated

        return objects

    raise RuntimeError(f"Response type {resp_type} not known")
```

### Prompts Afetados

Os seguintes prompts devem ser migrados para o formato JSONL:

| ID do Prompt | Descrição | Campo de Tipo |
|-----------|-------------|------------|
| `extract-definitions` | Extração de entidade/definição | Não (tipo único) |
| `extract-relationships` | Extração de relacionamento | Não (tipo único) |
| `extract-topics` | Extração de tópico/definição | Não (tipo único) |
| `extract-rows` | Extração de linha estruturada | Não (tipo único) |
| `agent-kg-extract` | Extração combinada de definição + relacionamento | Sim: `"definition"`, `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | Extração baseada em ontologia | Sim: `"entity"`, `"relationship"`, `"attribute"` |

### Alterações na API

#### Perspectiva do Cliente

A análise JSONL é transparente para os chamadores da API do serviço de prompt. A análise ocorre
no lado do servidor no serviço de prompt, e a resposta é retornada através do campo padrão
`PromptResponse.object` como um array JSON serializado.

Quando os clientes chamam o serviço de prompt (via `PromptClient.prompt()` ou similar):

**`response-type: "json"`** com esquema de array → o cliente recebe `list` do Python
**`response-type: "jsonl"`** → o cliente recebe `list` do Python

Da perspectiva do cliente, ambos retornam estruturas de dados idênticas. A
diferença está inteiramente em como a saída do LLM é analisada no lado do servidor:

Formato de array JSON: Uma única chamada `json.loads()`; falha completamente se truncado
Formato JSONL: Análise linha por linha; produz resultados parciais se truncado

Isso significa que o código do cliente existente que espera uma lista de prompts de extração
não requer alterações ao migrar prompts de JSON para JSONL.

#### Valor de Retorno do Servidor

Para `response-type: "jsonl"`, o método `PromptManager.invoke()` retorna um
`list[dict]` contendo todos os objetos analisados e validados com sucesso. Esta
lista é então serializada para JSON para o campo `PromptResponse.object`.

#### Tratamento de Erros

Resultados vazios: Retorna uma lista vazia `[]` com um log de aviso
Falha parcial na análise: Retorna uma lista de objetos analisados com sucesso com
  logs de aviso para as falhas
Falha completa na análise: Retorna uma lista vazia `[]` com logs de aviso

Isso difere de `response-type: "json"`, que lança `RuntimeError` em
caso de falha na análise. O comportamento tolerante para JSONL é intencional para fornecer
resiliência à truncagem.

### Exemplo de Configuração

Exemplo completo de configuração de prompt:

```json
{
  "prompt": "Extract all entities and their definitions from the following text. Output one JSON object per line.\n\nText:\n{{text}}\n\nOutput format per line:\n{\"entity\": \"<name>\", \"definition\": \"<definition>\"}",
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": {
        "type": "string",
        "description": "The entity name"
      },
      "definition": {
        "type": "string",
        "description": "A clear definition of the entity"
      }
    },
    "required": ["entity", "definition"]
  }
}
```

## Considerações de Segurança

**Validação de Entrada**: A análise JSON utiliza o padrão `json.loads()`, que é seguro
  contra ataques de injeção.
**Validação de Esquema**: Utiliza `jsonschema.validate()` para a aplicação do esquema.
**Sem Nova Superfície de Ataque**: A análise de JSONL é estritamente mais segura do que a análise de arrays JSON
  devido ao processamento linha por linha.

## Considerações de Desempenho

**Memória**: A análise linha por linha usa menos memória máxima do que o carregamento de arrays JSON completos.
  **Latência**: O desempenho da análise é comparável à análise de arrays JSON.
**Validação**: A validação de esquema é executada por objeto, o que adiciona sobrecarga, mas
permite resultados parciais em caso de falha na validação.
  

## Estratégia de Testes

### Testes Unitários

Análise de JSONL com entrada válida
Análise de JSONL com linhas vazias
Análise de JSONL com blocos de código Markdown
Análise de JSONL com linha final truncada
Análise de JSONL com linhas JSON inválidas intercaladas
Validação de esquema com uniões discriminadas `oneOf`
Compatibilidade com versões anteriores: prompts `"text"` e `"json"` existentes permanecem inalterados

### Testes de Integração

Extração ponta a ponta com prompts JSONL
Extração com truncamento simulado (resposta artificialmente limitada)
Extração de tipos mistos com discriminador de tipo
Extração de ontologia com todos os três tipos

### Testes de Qualidade de Extração

Compare os resultados da extração: formato JSONL versus array JSON.
Verifique a resiliência à truncagem: o JSONL produz resultados parciais onde o JSON falha.

## Plano de Migração

### Fase 1: Implementação

1. Implemente o método `parse_jsonl()` em `PromptManager`.
2. Estenda `invoke()` para lidar com `response-type: "jsonl"`.
3. Adicione testes unitários.

### Fase 2: Migração de Prompts

1. Atualize o prompt e a configuração `extract-definitions`.
2. Atualize o prompt e a configuração `extract-relationships`.
3. Atualize o prompt e a configuração `extract-topics`.
4. Atualize o prompt e a configuração `extract-rows`.
5. Atualize o prompt e a configuração `agent-kg-extract`.
6. Atualize o prompt e a configuração `extract-with-ontologies`.

### Fase 3: Atualizações para Sistemas Dependentes

1. Atualize qualquer código que consuma os resultados da extração para lidar com o tipo de retorno de lista.
2. Atualize o código que categoriza extrações de tipos mistos pelo campo `type`.
3. Atualize os testes que afirmam o formato da saída da extração.

## Perguntas Abertas

Nenhuma neste momento.

## Referências

Implementação atual: `trustgraph-flow/trustgraph/template/prompt_manager.py`
Especificação JSON Lines: https://jsonlines.org/
Esquema JSON `oneOf`: https://json-schema.org/understanding-json-schema/reference/combining.html#oneof
Especificação relacionada: Streaming LLM Responses (`docs/tech-specs/streaming-llm-responses.md`)
