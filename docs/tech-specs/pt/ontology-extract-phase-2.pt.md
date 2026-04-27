---
layout: default
title: "Extração de Conhecimento de Ontologias - Fase 2 de Refatoração"
parent: "Portuguese (Beta)"
---

# Extração de Conhecimento de Ontologias - Fase 2 de Refatoração

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**Status**: Rascunho
**Autor**: Sessão de Análise 2025-12-03
**Relacionado**: `ontology.md`, `ontorag.md`

## Visão Geral

Este documento identifica inconsistências no sistema atual de extração de conhecimento baseado em ontologias e propõe uma refatoração para melhorar o desempenho do LLM e reduzir a perda de informações.

## Implementação Atual

### Como Funciona Atualmente

1. **Carregamento da Ontologia** (`ontology_loader.py`)
   Carrega o arquivo JSON da ontologia com chaves como `"fo/Recipe"`, `"fo/Food"`, `"fo/produces"`
   Os IDs das classes incluem o prefixo do namespace na própria chave
   Exemplo de `food.ontology`:
     ```json
     "classes": {
       "fo/Recipe": {
         "uri": "http://purl.org/ontology/fo/Recipe",
         "rdfs:comment": "A Recipe is a combination..."
       }
     }
     ```

2. **Construção do Prompt** (`extract.py:299-307`, `ontology-prompt.md`)
   O modelo recebe os dicionários `classes`, `object_properties`, `datatype_properties`
   O modelo itera: `{% for class_id, class_def in classes.items() %}`
   O LLM vê: `**fo/Recipe**: A Recipe is a combination...`
   O formato de saída de exemplo mostra:
     ```json
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
     {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"}
     ```

3. **Análise da Resposta** (`extract.py:382-428`)
   Espera um array JSON: `[{"subject": "...", "predicate": "...", "object": "..."}]`
   Valida em relação a um subconjunto da ontologia
   Expande URIs via `expand_uri()` (extract.py:473-521)

4. **Expansão de URIs** (`extract.py:473-521`)
   Verifica se o valor está no dicionário `ontology_subset.classes`
   Se encontrado, extrai o URI da definição da classe
   Se não encontrado, constrói o URI: `f"https://trustgraph.ai/ontology/{ontology_id}#{value}"`

### Exemplo de Fluxo de Dados

**JSON da Ontologia → Loader → Prompt:**
```
"fo/Recipe" → classes["fo/Recipe"] → LLM sees "**fo/Recipe**"
```

**LLM → Parser → Output:**
```
"Recipe" → not in classes["fo/Recipe"] → constructs URI → LOSES original URI
"fo/Recipe" → found in classes → uses original URI → PRESERVES URI
```

## Problemas Identificados

### 1. **Exemplos Inconsistentes no Prompt**

**Problema**: O modelo de prompt mostra IDs de classe com prefixos (`fo/Recipe`), mas a saída de exemplo usa nomes de classe sem prefixo (`Recipe`).

**Localização**: `ontology-prompt.md:5-52`

```markdown
## Ontology Classes:
- **fo/Recipe**: A Recipe is...

## Example Output:
{"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
```

**Impacto**: O LLM recebe sinais conflitantes sobre qual formato usar.

### 2. **Perda de Informação na Expansão de URIs**

**Problema**: Quando o LLM retorna nomes de classe sem prefixo, seguindo o exemplo, `expand_uri()` não consegue encontrá-los no dicionário de ontologias e constrói URIs de fallback, perdendo os URIs originais corretos.

**Localização**: `extract.py:494-500`

```python
if value in ontology_subset.classes:  # Looks for "Recipe"
    class_def = ontology_subset.classes[value]  # But key is "fo/Recipe"
    if isinstance(class_def, dict) and 'uri' in class_def:
        return class_def['uri']  # Never reached!
return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"  # Fallback
```

**Impacto:**
URI original: `http://purl.org/ontology/fo/Recipe`
URI construído: `https://trustgraph.ai/ontology/food#Recipe`
Perda de significado semântico, quebra a interoperabilidade

### 3. **Formato Ambíguo de Instância de Entidade**

**Problema:** Não há orientação clara sobre o formato do URI da instância de entidade.

**Exemplos no prompt:**
`"recipe:cornish-pasty"` (prefixo semelhante a um namespace)
`"ingredient:flour"` (prefixo diferente)

**Comportamento real** (extract.py:517-520):
```python
# Treat as entity instance - construct unique URI
normalized = value.replace(" ", "-").lower()
return f"https://trustgraph.ai/{ontology_id}/{normalized}"
```

**Impacto**: O modelo de linguagem deve adivinhar a convenção de prefixo sem contexto ontológico.

### 4. **Sem Orientação de Prefixo de Namespace**

**Problema**: O JSON da ontologia contém definições de namespace (linha 10-25 em food.ontology):
```json
"namespaces": {
  "fo": "http://purl.org/ontology/fo/",
  "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  ...
}
```

Mas estas informações nunca são transmitidas para o LLM. O LLM não sabe:
O que "fo" significa
Qual prefixo usar para entidades
Qual namespace se aplica a quais elementos

### 5. **Rótulos Não Utilizados no Prompt**

**Problema**: Cada classe tem campos `rdfs:label` (por exemplo, `{"value": "Recipe", "lang": "en-gb"}`), mas o modelo de prompt não os utiliza.

**Atual**: Mostra apenas `class_id` e `comment`
```jinja
- **{{class_id}}**{% if class_def.comment %}: {{class_def.comment}}{% endif %}
```

**Disponível, mas não utilizado**:
```python
"rdfs:label": [{"value": "Recipe", "lang": "en-gb"}]
```

**Impacto**: Poderia fornecer nomes legíveis para humanos, juntamente com IDs técnicos.

## Soluções Propostas

### Opção A: Normalizar para IDs sem Prefixo

**Abordagem**: Remover os prefixos dos IDs de classe antes de exibi-los para o LLM.

**Alterações**:
1. Modificar `build_extraction_variables()` para transformar chaves:
   ```python
   classes_for_prompt = {
       k.split('/')[-1]: v  # "fo/Recipe" → "Recipe"
       for k, v in ontology_subset.classes.items()
   }
   ```

2. Atualizar o exemplo de prompt para corresponder (já usa nomes sem prefixo).

3. Modificar `expand_uri()` para lidar com ambos os formatos:
   ```python
   # Try exact match first
   if value in ontology_subset.classes:
       return ontology_subset.classes[value]['uri']

   # Try with prefix
   for prefix in ['fo/', 'rdf:', 'rdfs:']:
       prefixed = f"{prefix}{value}"
       if prefixed in ontology_subset.classes:
           return ontology_subset.classes[prefixed]['uri']
   ```

**Prós:**
Mais limpo, mais legível para humanos
Compatível com exemplos de prompts existentes
Modelos de linguagem grandes (LLMs) funcionam melhor com tokens mais simples

**Contras:**
Colisões de nomes de classe se múltiplas ontologias tiverem o mesmo nome de classe
Perde informações de namespace
Requer lógica de fallback para pesquisas

### Opção B: Usar IDs com Prefixo Completo Consistentemente

**Abordagem:** Atualizar exemplos para usar IDs com prefixo correspondentes ao que é mostrado na lista de classes.

**Mudanças:**
1. Atualizar exemplo de prompt (ontology-prompt.md:46-52):
   ```json
   [
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "fo/Recipe"},
     {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
     {"subject": "recipe:cornish-pasty", "predicate": "fo/produces", "object": "food:cornish-pasty"},
     {"subject": "food:cornish-pasty", "predicate": "rdf:type", "object": "fo/Food"}
   ]
   ```

2. Adicionar explicação do namespace ao prompt:
   ```markdown
   ## Namespace Prefixes:
   - **fo/**: Food Ontology (http://purl.org/ontology/fo/)
   - **rdf:**: RDF Schema
   - **rdfs:**: RDF Schema

   Use these prefixes exactly as shown when referencing classes and properties.
   ```

3. Mantenha `expand_uri()` como está (funciona corretamente quando as correspondências são encontradas).

**Prós:**
Consistência entre entrada e saída.
Sem perda de informação.
Preserva a semântica do namespace.
Funciona com múltiplas ontologias.

**Contras:**
Tokens mais verbosos para o LLM.
Requer que o LLM rastreie os prefixos.

### Opção C: Híbrida - Mostrar Tanto o Rótulo quanto o ID

**Abordagem:** Aprimorar o prompt para mostrar tanto os rótulos legíveis por humanos quanto os IDs técnicos.

**Alterações:**
1. Atualizar o modelo do prompt:
   ```jinja
   {% for class_id, class_def in classes.items() %}
   - **{{class_id}}** (label: "{{class_def.labels[0].value if class_def.labels else class_id}}"){% if class_def.comment %}: {{class_def.comment}}{% endif %}
   {% endfor %}
   ```

   Exemplo de saída:
   ```markdown
   - **fo/Recipe** (label: "Recipe"): A Recipe is a combination...
   ```

2. Instruções de atualização:
   ```markdown
   When referencing classes:
   - Use the full prefixed ID (e.g., "fo/Recipe") in JSON output
   - The label (e.g., "Recipe") is for human understanding only
   ```

**Prós**:
Mais claro para LLM
Preserva todas as informações
Explícito sobre o que usar

**Contras**:
Prompt mais longo
Modelo mais complexo

## Abordagem Implementada

**Formato Simplificado de Entidade-Relacionamento-Atributo** - substitui completamente o formato antigo baseado em triplas.

A nova abordagem foi escolhida porque:

1. **Nenhuma Perda de Informação**: URIs originais preservados corretamente
2. **Lógica Mais Simples**: Nenhuma transformação necessária, pesquisas diretas em dicionários funcionam
3. **Segurança de Namespace**: Lida com múltiplas ontologias sem colisões
4. **Correção Semântica**: Mantém a semântica RDF/OWL

## Implementação Completa

### O Que Foi Construído:

1. **Novo Modelo de Prompt** (`prompts/ontology-extract-v2.txt`)
   ✅ Seções claras: Tipos de Entidade, Relacionamentos, Atributos
   ✅ Exemplo usando identificadores de tipo completos (`fo/Recipe`, `fo/has_ingredient`)
   ✅ Instruções para usar identificadores exatos do esquema
   ✅ Novo formato JSON com arrays de entidades/relacionamentos/atributos

2. **Normalização de Entidade** (`entity_normalizer.py`)
   ✅ `normalize_entity_name()` - Converte nomes para formato seguro para URI
   ✅ `normalize_type_identifier()` - Lida com barras em tipos (`fo/Recipe` → `fo-recipe`)
   ✅ `build_entity_uri()` - Cria URIs únicos usando a tupla (nome, tipo)
   ✅ `EntityRegistry` - Rastreia entidades para desduplicação

3. **Analisador JSON** (`simplified_parser.py`)
   ✅ Analisa o novo formato: `{entities: [...], relationships: [...], attributes: [...]}`
   ✅ Suporta nomes de campos em kebab-case e snake_case
   ✅ Retorna dataclasses estruturadas
   ✅ Tratamento de erros elegante com registro

4. **Conversor de Triplas** (`triple_converter.py`)
   ✅ `convert_entity()` - Gera automaticamente triplas de tipo + rótulo
   ✅ `convert_relationship()` - Conecta URIs de entidade via propriedades
   ✅ `convert_attribute()` - Adiciona valores literais
   ✅ Consulta URIs completos a partir de definições de ontologia

5. **Processador Principal Atualizado** (`extract.py`)
   ✅ Removeu o código antigo de extração baseado em triplas
   ✅ Adicionado método `extract_with_simplified_format()`
   ✅ Agora usa exclusivamente o novo formato simplificado
   ✅ Chama o prompt com o ID `extract-with-ontologies-v2`

## Casos de Teste

### Teste 1: Preservação de URI
```python
# Given ontology class
classes = {"fo/Recipe": {"uri": "http://purl.org/ontology/fo/Recipe", ...}}

# When LLM returns
llm_output = {"subject": "x", "predicate": "rdf:type", "object": "fo/Recipe"}

# Then expanded URI should be
assert expanded == "http://purl.org/ontology/fo/Recipe"
# Not: "https://trustgraph.ai/ontology/food#Recipe"
```

### Teste 2: Colisão Multi-Ontologia
```python
# Given two ontologies
ont1 = {"fo/Recipe": {...}}
ont2 = {"cooking/Recipe": {...}}

# LLM should use full prefix to disambiguate
llm_output = {"object": "fo/Recipe"}  # Not just "Recipe"
```

### Teste 3: Formato de Instância de Entidade
```python
# Given prompt with food ontology
# LLM should create instances like
{"subject": "recipe:cornish-pasty"}  # Namespace-style
{"subject": "food:beef"}              # Consistent prefix
```

## Perguntas Abertas

1. **As instâncias de entidades devem usar prefixos de namespace?**
   Atual: `"recipe:cornish-pasty"` (arbitrário)
   Alternativa: Usar o prefixo da ontologia `"fo:cornish-pasty"`?
   Alternativa: Sem prefixo, expandir no URI `"cornish-pasty"` → URI completo?

2. **Como lidar com o domínio/alcance no prompt?**
   Atualmente mostra: `(Recipe → Food)`
   Deveria ser: `(fo/Recipe → fo/Food)`?

3. **Devemos validar as restrições de domínio/alcance?**
   TODO: comentário em extract.py:470
   Detectaria mais erros, mas seria mais complexo

4. **O que dizer das propriedades inversas e equivalências?**
   A ontologia tem `owl:inverseOf`, `owl:equivalentClass`
   Não está atualmente sendo usado na extração
   Deveria estar?

## Métricas de Sucesso

✅ Perda zero de informações de URI (100% de preservação dos URIs originais)
✅ O formato de saída do LLM corresponde ao formato de entrada
✅ Nenhum exemplo ambíguo no prompt
✅ Os testes passam com múltiplas ontologias
✅ Qualidade de extração aprimorada (medida pela porcentagem de triplas válidas)

## Abordagem Alternativa: Formato de Extração Simplificado

### Filosofia

Em vez de pedir ao LLM para entender a semântica RDF/OWL, peça para ele fazer o que ele faz de melhor: **encontrar entidades e relacionamentos no texto**.

Deixe que o código lide com a construção de URIs, a conversão RDF e as formalidades da web semântica.

### Exemplo: Classificação de Entidades

**Texto de Entrada:**
```
Cornish pasty is a traditional British pastry filled with meat and vegetables.
```

**Esquema de Ontologia (mostrado ao LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food
```

**O que o LLM retorna (JSON simples):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    }
  ]
}
```

**O que o Código Produz (Triplas RDF):**
```python
# 1. Normalize entity name + type to ID (type prevents collisions)
entity_id = "recipe-cornish-pasty"  # normalize("Cornish pasty", "Recipe")
entity_uri = "https://trustgraph.ai/food/recipe-cornish-pasty"

# Note: Same name, different type = different URI
# "Cornish pasty" (Recipe) → recipe-cornish-pasty
# "Cornish pasty" (Food) → food-cornish-pasty

# 2. Generate triples
triples = [
    # Type triple
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),
    # Label triple (automatic)
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
        o=Value(value="Cornish pasty", is_uri=False)
    )
]
```

### Benefícios

1. **O LLM não precisa de:**
   Entender a sintaxe de URI
   Inventar prefixos de identificadores (`recipe:`, `ingredient:`)
   Saber sobre `rdf:type` ou `rdfs:label`
   Construir identificadores da web semântica

2. **O LLM precisa apenas de:**
   Encontrar entidades no texto
   Mapeá-las para classes de ontologia
   Extrair relacionamentos e atributos

3. **O código lida com:**
   Normalização e construção de URI
   Geração de triplas RDF
   Atribuição automática de rótulos
   Gerenciamento de namespaces

### Por que Isso Funciona Melhor

**Prompt mais simples** = menos confusão = menos erros
**IDs consistentes** = o código controla as regras de normalização
**Rótulos gerados automaticamente** = sem triplas rdfs:label ausentes
**O LLM se concentra na extração** = o que ele realmente faz bem

### Exemplo: Relacionamentos de Entidades

**Texto de entrada:**
```
Cornish pasty is a traditional British pastry filled with beef and potatoes.
```

**Esquema de Ontologia (mostrado ao LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food

## Relationships:
- has_ingredient: Relates a recipe to an ingredient it uses (Recipe → Ingredient)
- food: Relates an ingredient to the food that is required (Ingredient → Food)
```

**O que o LLM retorna (JSON simples):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ]
}
```

**O que o Código Produz (Triplas RDF):**
```python
# Normalize entity names to URIs
cornish_pasty_uri = "https://trustgraph.ai/food/cornish-pasty"
beef_uri = "https://trustgraph.ai/food/beef"
potatoes_uri = "https://trustgraph.ai/food/potatoes"

# Look up relation URI from ontology
has_ingredient_uri = "http://purl.org/ontology/fo/ingredients"  # from fo/has_ingredient

triples = [
    # Entity type triples (as before)
    Triple(s=cornish_pasty_uri, p=rdf_type, o="http://purl.org/ontology/fo/Recipe"),
    Triple(s=cornish_pasty_uri, p=rdfs_label, o="Cornish pasty"),

    Triple(s=beef_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=beef_uri, p=rdfs_label, o="beef"),

    Triple(s=potatoes_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=potatoes_uri, p=rdfs_label, o="potatoes"),

    # Relationship triples
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=beef_uri, is_uri=True)
    ),
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=potatoes_uri, is_uri=True)
    )
]
```

**Pontos-chave:**
O LLM retorna nomes de entidades em linguagem natural: `"Cornish pasty"`, `"beef"`, `"potatoes"`
O LLM inclui tipos para disambiguar: `subject-type`, `object-type`
O LLM usa o nome da relação do esquema: `"has_ingredient"`
O código deriva IDs consistentes usando (nome, tipo): `("Cornish pasty", "Recipe")` → `recipe-cornish-pasty`
O código pesquisa o URI da relação na ontologia: `fo/has_ingredient` → URI completo
A mesma tupla (nome, tipo) sempre obtém o mesmo URI (desduplicação)

### Exemplo: Desambiguação de Nomes de Entidades

**Problema:** O mesmo nome pode se referir a diferentes tipos de entidade.

**Caso real:**
```
"Cornish pasty" can be:
- A Recipe (instructions for making it)
- A Food (the dish itself)
```

**Como é tratado:**

O LLM retorna ambos como entidades separadas:
```json
{
  "entities": [
    {"entity": "Cornish pasty", "type": "Recipe"},
    {"entity": "Cornish pasty", "type": "Food"}
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "produces",
      "object": "Cornish pasty",
      "object-type": "Food"
    }
  ]
}
```

**Resolução de Código:**
```python
# Different types → different URIs
recipe_uri = normalize("Cornish pasty", "Recipe")
# → "https://trustgraph.ai/food/recipe-cornish-pasty"

food_uri = normalize("Cornish pasty", "Food")
# → "https://trustgraph.ai/food/food-cornish-pasty"

# Relationship connects them correctly
triple = Triple(
    s=recipe_uri,  # The Recipe
    p="http://purl.org/ontology/fo/produces",
    o=food_uri     # The Food
)
```

**Por que isso funciona:**
O tipo está incluído em TODAS as referências (entidades, relacionamentos, atributos).
O código usa a tupla `(name, type)` como chave de pesquisa.
Sem ambiguidades, sem colisões.

### Exemplo: Atributos de Entidade

**Texto de entrada:**
```
This Cornish pasty recipe serves 4-6 people and takes 45 minutes to prepare.
```

**Esquema de Ontologia (mostrado ao LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method

## Attributes:
- serves: Indicates what the recipe is intended to serve (Recipe → text)
- preparation_time: Time needed to prepare the recipe (Recipe → text)
```

**O que o LLM retorna (JSON simples):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty recipe",
      "type": "Recipe"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4-6 people"
    },
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "preparation_time",
      "value": "45 minutes"
    }
  ]
}
```

**O que o Código Produz (Triplas RDF):**
```python
# Normalize entity name to URI
recipe_uri = "https://trustgraph.ai/food/cornish-pasty-recipe"

# Look up attribute URIs from ontology
serves_uri = "http://purl.org/ontology/fo/serves"  # from fo/serves
prep_time_uri = "http://purl.org/ontology/fo/preparation_time"  # from fo/preparation_time

triples = [
    # Entity type triple
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdf_type, is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),

    # Label triple (automatic)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdfs_label, is_uri=True),
        o=Value(value="Cornish pasty recipe", is_uri=False)
    ),

    # Attribute triples (objects are literals, not URIs)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=serves_uri, is_uri=True),
        o=Value(value="4-6 people", is_uri=False)  # Literal value!
    ),
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=prep_time_uri, is_uri=True),
        o=Value(value="45 minutes", is_uri=False)  # Literal value!
    )
]
```

**Pontos-chave:**
O LLM extrai valores literais: `"4-6 people"`, `"45 minutes"`
O LLM inclui o tipo de entidade para desambiguação: `entity-type`
O LLM usa o nome do atributo do esquema: `"serves"`, `"preparation_time"`
O código pesquisa o URI do atributo a partir das propriedades do tipo de dados da ontologia
**O objeto é literal** (`is_uri=False`), não uma referência de URI
Os valores permanecem como texto natural, sem necessidade de normalização

**Diferença em relação a Relacionamentos:**
Relacionamentos: tanto o sujeito quanto o objeto são entidades (URIs)
Atributos: o sujeito é uma entidade (URI), o objeto é um valor literal (string/número)

### Exemplo Completo: Entidades + Relacionamentos + Atributos

**Texto de Entrada:**
```
Cornish pasty is a savory pastry filled with beef and potatoes.
This recipe serves 4 people.
```

**O que o LLM retorna:**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4 people"
    }
  ]
}
```

**Resultado:** 11 triplas RDF geradas:
3 triplas de tipo de entidade (rdf:type)
3 triplas de rótulo de entidade (rdfs:label) - automático
2 triplas de relacionamento (has_ingredient)
1 tripla de atributo (serves)

Tudo isso a partir de extrações simples e em linguagem natural pelo LLM!

## Referências

Implementação atual: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`
Modelo de prompt: `ontology-prompt.md`
Casos de teste: `tests/unit/test_extract/test_ontology/`
Ontologia de exemplo: `e2e/test-data/food.ontology`
