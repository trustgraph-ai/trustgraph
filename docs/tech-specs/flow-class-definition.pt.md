---
layout: default
title: "Especificação da Definição do Modelo de Fluxo"
parent: "Portuguese (Beta)"
---

# Especificação da Definição do Modelo de Fluxo

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visão Geral

Um modelo de fluxo define um modelo de padrão de fluxo de dados completo no sistema TrustGraph. Quando instanciado, ele cria uma rede interconectada de processadores que lidam com a ingestão, o processamento, o armazenamento e a consulta de dados como um sistema unificado.

## Estrutura

Uma definição de modelo de fluxo consiste em cinco seções principais:

### 1. Seção de Classe
Define processadores de serviço compartilhados que são instanciados uma vez por modelo de fluxo. Esses processadores lidam com solicitações de todas as instâncias de fluxo desta classe.

```json
"class": {
  "service-name:{class}": {
    "request": "queue-pattern:{class}",
    "response": "queue-pattern:{class}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**Características:**
Compartilhadas entre todas as instâncias de fluxo da mesma classe.
<<<<<<< HEAD
Normalmente, serviços caros ou sem estado (LLMs, modelos de embedding).
=======
Normalmente, serviços com alto custo ou sem estado (LLMs, modelos de embedding).
>>>>>>> 82edf2d (New md files from RunPod)
Use a variável de modelo `{class}` para o nome da fila.
As configurações podem ser valores fixos ou parametrizadas com a sintaxe `{parameter-name}`.
Exemplos: `embeddings:{class}`, `text-completion:{class}`, `graph-rag:{class}`.

### 2. Seção de Fluxo
Define processadores específicos do fluxo que são instanciados para cada instância de fluxo individual. Cada fluxo recebe seu próprio conjunto isolado desses processadores.

```json
"flow": {
  "processor-name:{id}": {
    "input": "queue-pattern:{id}",
    "output": "queue-pattern:{id}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**Características:**
Instância única por fluxo
Gerenciar dados e estado específicos do fluxo
<<<<<<< HEAD
Usar variável de modelo `{id}` para nomeação de filas
As configurações podem ser valores fixos ou parametrizados com a sintaxe `{parameter-name}`
Exemplos: `chunker:{id}`, `pdf-decoder:{id}`, `kg-extract-relationships:{id}`

### 3. Seção de Interfaces
Define os pontos de entrada e os contratos de interação para o fluxo. Estes formam a superfície da API para sistemas externos e comunicação entre componentes internos.
=======
Usar variável de modelo `{id}` para nomeação de fila
As configurações podem ser valores fixos ou parametrizadas com a sintaxe `{parameter-name}`
Exemplos: `chunker:{id}`, `pdf-decoder:{id}`, `kg-extract-relationships:{id}`

### 3. Seção de Interfaces
Define os pontos de entrada e os contratos de interação para o fluxo. Estes formam a superfície da API para sistemas externos e comunicação de componentes internos.
>>>>>>> 82edf2d (New md files from RunPod)

As interfaces podem assumir duas formas:

**Padrão Fire-and-Forget** (uma única fila):
```json
"interfaces": {
  "document-load": "persistent://tg/flow/document-load:{id}",
  "triples-store": "persistent://tg/flow/triples-store:{id}"
}
```

**Padrão de Requisição/Resposta** (objeto com campos de requisição/resposta):
```json
"interfaces": {
  "embeddings": {
    "request": "non-persistent://tg/request/embeddings:{class}",
    "response": "non-persistent://tg/response/embeddings:{class}"
  }
}
```

**Tipos de Interfaces:**
**Pontos de Entrada**: Onde sistemas externos injetam dados (`document-load`, `agent`)
**Interfaces de Serviço**: Padrões de solicitação/resposta para serviços (`embeddings`, `text-completion`)
**Interfaces de Dados**: Pontos de conexão de fluxo de dados do tipo "enviar e esquecer" (`triples-store`, `entity-contexts-load`)

### 4. Seção de Parâmetros
Mapeia nomes de parâmetros específicos do fluxo para definições de parâmetros armazenadas centralmente:

```json
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "chunk": "chunk-size"
}
```

**Características:**
As chaves são nomes de parâmetros usados nas configurações do processador (por exemplo, `{model}`)
Os valores referenciam as definições de parâmetros armazenadas em schema/config
Permite a reutilização de definições de parâmetros comuns em diferentes fluxos
Reduz a duplicação de esquemas de parâmetros

### 5. Metadados
Informações adicionais sobre o blueprint do fluxo:

```json
"description": "Human-readable description",
"tags": ["capability-1", "capability-2"]
```

## Variáveis de Modelo

### Variáveis do Sistema

#### {id}
<<<<<<< HEAD
Substituído pelo identificador de instância de fluxo único.
=======
Substituído pelo identificador único da instância do fluxo.
>>>>>>> 82edf2d (New md files from RunPod)
Cria recursos isolados para cada fluxo.
Exemplo: `flow-123`, `customer-A-flow`

#### {class}
Substituído pelo nome do blueprint do fluxo.
Cria recursos compartilhados entre fluxos da mesma classe.
Exemplo: `standard-rag`, `enterprise-rag`

### Variáveis de Parâmetro

#### {parameter-name}
Parâmetros personalizados definidos no momento da execução do fluxo.
Os nomes dos parâmetros correspondem às chaves na seção `parameters` do fluxo.
Usados em configurações do processador para personalizar o comportamento.
Exemplos: `{model}`, `{temp}`, `{chunk}`
Substituído pelos valores fornecidos ao iniciar o fluxo.
Validado em relação às definições de parâmetros armazenadas centralmente.

## Configurações do Processador

As configurações fornecem valores de configuração aos processadores no momento da instanciação. Elas podem ser:

### Configurações Fixas
Valores diretos que não mudam:
```json
"settings": {
  "model": "gemma3:12b",
  "temperature": 0.7,
  "max_retries": 3
}
```

### Configurações Parametrizadas
Valores que utilizam parâmetros fornecidos no lançamento do fluxo:
```json
"settings": {
  "model": "{model}",
  "temperature": "{temp}",
  "endpoint": "https://{region}.api.example.com"
}
```

Os nomes dos parâmetros nas configurações correspondem às chaves na seção `parameters` do fluxo.

### Exemplos de Configurações

**Processador LLM com Parâmetros:**
```json
// In parameters section:
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "tokens": "max-tokens",
  "key": "openai-api-key"
}

// In processor definition:
"text-completion:{class}": {
  "request": "non-persistent://tg/request/text-completion:{class}",
  "response": "non-persistent://tg/response/text-completion:{class}",
  "settings": {
    "model": "{model}",
    "temperature": "{temp}",
    "max_tokens": "{tokens}",
    "api_key": "{key}"
  }
}
```

**Chunker com Configurações Fixas e Parametrizadas:**
```json
// In parameters section:
"parameters": {
  "chunk": "chunk-size"
}

// In processor definition:
"chunker:{id}": {
  "input": "persistent://tg/flow/chunk:{id}",
  "output": "persistent://tg/flow/chunk-load:{id}",
  "settings": {
    "chunk_size": "{chunk}",
    "chunk_overlap": 100,
    "encoding": "utf-8"
  }
}
```

## Padrões de Filas (Pulsar)

Os modelos de fluxo utilizam o Apache Pulsar para mensagens. Os nomes das filas seguem o formato do Pulsar:
```
<persistence>://<tenant>/<namespace>/<topic>
```

### Componentes:
**persistência**: `persistent` ou `non-persistent` (modo de persistência do Pulsar)
<<<<<<< HEAD
**inquilino**: `tg` para definições de blueprint de fluxo fornecidas pelo TrustGraph
=======
**inquilino**: `tg` para definições de blueprint de fluxo fornecidas pela TrustGraph
>>>>>>> 82edf2d (New md files from RunPod)
**namespace**: Indica o padrão de mensagens
  `flow`: Serviços de envio e esquecimento
  `request`: Parte de solicitação de serviços de solicitação/resposta
  `response`: Parte de resposta de serviços de solicitação/resposta
**tópico**: O nome específico da fila/tópico com variáveis de modelo

### Filas Persistentes
Padrão: `persistent://tg/flow/<topic>:{id}`
Usado para serviços de envio e esquecimento e fluxo de dados durável
Os dados persistem no armazenamento do Pulsar durante as reinicializações
Exemplo: `persistent://tg/flow/chunk-load:{id}`

### Filas Não Persistentes
Padrão: `non-persistent://tg/request/<topic>:{class}` ou `non-persistent://tg/response/<topic>:{class}`
Usado para padrões de mensagens de solicitação/resposta
Efêmeras, não persistidas em disco pelo Pulsar
Menor latência, adequado para comunicação no estilo RPC
Exemplo: `non-persistent://tg/request/embeddings:{class}`

## Arquitetura do Fluxo de Dados

O blueprint do fluxo cria um fluxo de dados unificado onde:

<<<<<<< HEAD
1. **Pipeline de Processamento de Documentos**: Fluxo da ingestão ao processamento e armazenamento
2. **Serviços de Consulta**: Processadores integrados que consultam os mesmos armazenamentos de dados e serviços
3. **Serviços Compartilhados**: Processadores centralizados que todos os fluxos podem utilizar
4. **Escritores de Armazenamento**: Persistem os dados processados em armazenamentos apropriados
=======
1. **Pipeline de Processamento de Documentos**: Fluxo da ingestão ao armazenamento, passando pela transformação
2. **Serviços de Consulta**: Processadores integrados que consultam os mesmos armazenamentos de dados e serviços
3. **Serviços Compartilhados**: Processadores centralizados que todos os fluxos podem utilizar
4. **Escritores de Armazenamento**: Persistem os dados processados nos armazenamentos apropriados
>>>>>>> 82edf2d (New md files from RunPod)

Todos os processadores (tanto `{id}` quanto `{class}`) trabalham juntos como um grafo de fluxo de dados coeso, e não como sistemas separados.

## Exemplo de Instanciação de Fluxo

Dado:
ID da Instância do Fluxo: `customer-A-flow`
Blueprint do Fluxo: `standard-rag`
Mapeamentos de parâmetros do fluxo:
  `"model": "llm-model"`
  `"temp": "temperature"`
  `"chunk": "chunk-size"`
Parâmetros fornecidos pelo usuário:
  `model`: `gpt-4`
  `temp`: `0.5`
  `chunk`: `512`

Expansões de modelo:
`persistent://tg/flow/chunk-load:{id}` → `persistent://tg/flow/chunk-load:customer-A-flow`
`non-persistent://tg/request/embeddings:{class}` → `non-persistent://tg/request/embeddings:standard-rag`
`"model": "{model}"` → `"model": "gpt-4"`
`"temperature": "{temp}"` → `"temperature": "0.5"`
`"chunk_size": "{chunk}"` → `"chunk_size": "512"`

Isso cria:
Pipeline de processamento de documentos isolado para `customer-A-flow`
Serviço de incorporação compartilhado para todos os fluxos `standard-rag`
<<<<<<< HEAD
Fluxo de dados completo da ingestão de documentos à consulta
=======
Fluxo de dados completo da ingestão do documento à consulta
>>>>>>> 82edf2d (New md files from RunPod)
Processadores configurados com os valores de parâmetro fornecidos

## Benefícios

1. **Eficiência de Recursos**: Serviços caros são compartilhados entre os fluxos
2. **Isolamento de Fluxo**: Cada fluxo tem seu próprio pipeline de processamento de dados
3. **Escalabilidade**: É possível instanciar vários fluxos do mesmo modelo
4. **Modularidade**: Separação clara entre componentes compartilhados e específicos do fluxo
5. **Arquitetura Unificada**: Consulta e processamento fazem parte do mesmo fluxo de dados
