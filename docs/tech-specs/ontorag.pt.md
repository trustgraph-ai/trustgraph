# OntoRAG: Especificação Técnica de Extração e Consulta de Conhecimento Baseada em Ontologia

## Visão Geral

OntoRAG é um sistema de extração e consulta de conhecimento orientado por ontologia que impõe uma consistência semântica rigorosa durante a extração de triplas de conhecimento de texto não estruturado e durante a consulta do grafo de conhecimento resultante. Semelhante ao GraphRAG, mas com restrições de ontologia formais, o OntoRAG garante que todas as triplas extraídas estejam em conformidade com estruturas ontológicas predefinidas e fornece recursos de consulta com consciência semântica.

O sistema usa correspondência de similaridade vetorial para selecionar dinamicamente subconjuntos de ontologia relevantes para operações de extração e consulta, permitindo um processamento focado e contextualmente apropriado, mantendo a validade semântica.

**Nome do Serviço**: `kg-extract-ontology`

## Objetivos

**Extração Conforme à Ontologia**: Garantir que todas as triplas extraídas estejam estritamente em conformidade com as ontologias carregadas.
**Seleção de Contexto Dinâmico**: Usar incorporações para selecionar subconjuntos de ontologia relevantes para cada trecho.
**Consistência Semântica**: Manter hierarquias de classes, domínios/intervalos de propriedades e restrições.
**Processamento Eficiente**: Usar armazenamentos vetoriais em memória para correspondência rápida de elementos de ontologia.
**Arquitetura Escalável**: Suportar múltiplas ontologias concorrentes com diferentes domínios.

## Contexto

Os serviços atuais de extração de conhecimento (`kg-extract-definitions`, `kg-extract-relationships`) operam sem restrições formais, potencialmente produzindo triplas inconsistentes ou incompatíveis. O OntoRAG aborda isso através de:

1. Carregamento de ontologias formais que definem classes e propriedades válidas.
2. Uso de incorporações para corresponder o conteúdo do texto com elementos de ontologia relevantes.
3. Restringir a extração para produzir apenas triplas conformes à ontologia.
4. Fornecer validação semântica do conhecimento extraído.

Essa abordagem combina a flexibilidade da extração neural com a precisão da representação formal do conhecimento.

## Design Técnico

### Arquitetura

O sistema OntoRAG consiste nos seguintes componentes:

```
┌─────────────────┐
│  Configuration  │
│    Service      │
└────────┬────────┘
         │ Ontologies
         ▼
┌─────────────────┐      ┌──────────────┐
│ kg-extract-     │────▶│  Embedding   │
│   ontology      │      │   Service    │
└────────┬────────┘      └──────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐      ┌──────────────┐
│   In-Memory     │◀────│   Ontology   │
│  Vector Store   │      │   Embedder   │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Sentence     │────▶│   Chunker    │
│    Splitter     │      │   Service    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Ontology     │────▶│   Vector     │
│    Selector     │      │   Search     │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Prompt       │────▶│   Prompt     │
│   Constructor   │      │   Service    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  Triple Output  │
└─────────────────┘
```

### Detalhes do Componente

#### 1. Carregador de Ontologia

**Propósito**: Recupera e analisa configurações de ontologia do serviço de configuração usando atualizações orientadas a eventos.

**Implementação**:
O Carregador de Ontologia usa a fila ConfigPush da TrustGraph para receber atualizações orientadas a eventos de configuração de ontologia. Quando um elemento de configuração do tipo "ontologia" é adicionado ou modificado, o carregador recebe a atualização através da fila config-update e analisa a estrutura JSON contendo metadados, classes, propriedades de objeto e propriedades de tipo de dados. Essas ontologias analisadas são armazenadas na memória como objetos estruturados que podem ser acessados de forma eficiente durante o processo de extração.

**Operações Chave**:
Assinar a fila config-update para configurações do tipo ontologia
Analisar estruturas JSON de ontologia em objetos OntologyClass e OntologyProperty
Validar a estrutura e a consistência da ontologia
Armazenar em cache as ontologias analisadas na memória para acesso rápido
Lidar com o processamento por fluxo com armazenamentos de vetores específicos do fluxo

**Localização da Implementação**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_loader.py`

#### 2. Incorporador de Ontologia

**Propósito**: Cria incorporações vetoriais para todos os elementos da ontologia para permitir a correspondência de similaridade semântica.

**Implementação**:
O Incorporador de Ontologia processa cada elemento nas ontologias carregadas (classes, propriedades de objeto e propriedades de tipo de dados) e gera incorporações vetoriais usando o serviço EmbeddingsClientSpec. Para cada elemento, ele combina o identificador do elemento, os rótulos e a descrição (comentário) para criar uma representação de texto. Este texto é então convertido em uma incorporação vetorial de alta dimensão que captura seu significado semântico. Essas incorporações são armazenadas em um armazenamento de vetores FAISS na memória, específico para cada fluxo, juntamente com metadados sobre o tipo de elemento, a ontologia de origem e a definição completa. O incorporador detecta automaticamente a dimensão da incorporação a partir da primeira resposta de incorporação.

**Operações Chave**:
Criar representações de texto a partir de IDs de elementos, rótulos e comentários
Gerar incorporações via EmbeddingsClientSpec (usando asyncio.gather para processamento em lote)
Armazenar incorporações com metadados abrangentes no armazenamento de vetores FAISS
Indexar por ontologia, tipo de elemento e ID de elemento para recuperação eficiente
Detectar automaticamente as dimensões da incorporação para a inicialização do armazenamento de vetores
Lidar com modelos de incorporação específicos do fluxo com armazenamentos de vetores independentes

**Localização da Implementação**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_embedder.py`

#### 3. Processador de Texto (Divisor de Sentenças)

**Propósito**: Decompõe blocos de texto em segmentos granulares para correspondência precisa de ontologia.

**Implementação**:
O Processador de Texto usa NLTK para tokenização de sentenças e marcação POS para dividir os blocos de texto recebidos em sentenças. Ele lida com a compatibilidade de versão do NLTK tentando baixar `punkt_tab` e `averaged_perceptron_tagger_eng`, com fallback para versões mais antigas, se necessário. Cada bloco de texto é dividido em sentenças individuais que podem ser correspondidas independentemente com elementos de ontologia.

**Operações Chave**:
Dividir o texto em sentenças usando a tokenização de sentenças do NLTK
Lidar com a compatibilidade de versão do NLTK (punkt_tab vs punkt)
Criar objetos TextSegment com texto e informações de posição
Suportar tanto sentenças completas quanto blocos individuais

**Localização da Implementação**: `trustgraph-flow/trustgraph/extract/kg/ontology/text_processor.py`

#### 4. Selecionador de Ontologia

**Propósito**: Identifica o subconjunto mais relevante de elementos de ontologia para o bloco de texto atual.

**Implementação**:
O Selecionador de Ontologia realiza a correspondência semântica entre segmentos de texto e elementos de ontologia usando a pesquisa de similaridade vetorial FAISS. Para cada sentença do bloco de texto, ele gera uma incorporação e pesquisa o armazenamento de vetores pelos elementos de ontologia mais semelhantes usando a similaridade de cossenos com um limite configurável (padrão 0,3). Após coletar todos os elementos relevantes, ele realiza a resolução de dependências abrangente: se uma classe é selecionada, suas classes pai são incluídas; se uma propriedade é selecionada, suas classes de domínio e intervalo são adicionadas. Além disso, para cada classe selecionada, ele inclui automaticamente **todas as propriedades que referenciam essa classe** em seu domínio ou intervalo. Isso garante que a extração tenha acesso a todas as propriedades relevantes.

**Operações Chave**:
Gerar incorporações para cada segmento de texto (frases)
Realizar busca de vizinhos mais próximos em k no armazenamento vetorial FAISS (top_k=10, threshold=0.3)
Aplicar um limite de similaridade para filtrar correspondências fracas
Resolver dependências (classes pai, domínios, intervalos)
**Incluir automaticamente todas as propriedades relacionadas às classes selecionadas** (correspondência de domínio/intervalo)
Construir um subconjunto de ontologia coerente com todos os relacionamentos necessários
Eliminar elementos duplicados que aparecem várias vezes

**Localização da Implementação**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_selector.py`

#### 5. Construção do Prompt

**Propósito**: Cria prompts estruturados que orientam o LLM a extrair apenas triplas conformes à ontologia.

**Implementação**:
O serviço de extração usa um modelo Jinja2 carregado de `ontology-prompt.md` que formata o subconjunto da ontologia e o texto para a extração do LLM. O modelo itera dinamicamente sobre classes, propriedades de objeto e propriedades de tipo de dados usando a sintaxe Jinja2, apresentando cada uma com suas descrições, domínios, intervalos e relacionamentos hierárquicos. O prompt inclui regras estritas sobre o uso apenas dos elementos da ontologia fornecidos e solicita um formato de saída JSON para análise consistente.

**Operações Chave**:
Usar modelo Jinja2 com loops sobre elementos da ontologia
Formatar classes com relacionamentos pai (subclass_of) e comentários
Formatar propriedades com restrições de domínio/intervalo e comentários
Incluir regras de extração explícitas e requisitos de formato de saída
Chamar o serviço de prompt com o ID do modelo "extract-with-ontologies"

**Localização do Modelo**: `ontology-prompt.md`
**Localização da Implementação**: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py` (método build_extraction_variables)

#### 6. Serviço Principal de Extração

**Propósito**: Coordena todos os componentes para realizar a extração de triplas baseada em ontologia de ponta a ponta.

**Implementação**:
O Serviço Principal de Extração (KgExtractOntology) é a camada de orquestração que gerencia todo o fluxo de trabalho de extração. Ele usa o padrão FlowProcessor da TrustGraph com inicialização de componentes específica para cada fluxo. Quando uma atualização de configuração da ontologia é recebida, ele inicializa ou atualiza os componentes específicos do fluxo (carregador de ontologia, incorporador, processador de texto, selecionador). Quando um trecho de texto chega para processamento, ele coordena o pipeline: dividindo o texto em segmentos, encontrando elementos de ontologia relevantes por meio de busca vetorial, construindo um prompt restrito, chamando o serviço de prompt, analisando e validando a resposta, gerando triplas de definição de ontologia e emitindo tanto triplas de conteúdo quanto contextos de entidade.

**Pipeline de Extração**:
1. Receber trecho de texto via fila chunks-input
2. Inicializar componentes do fluxo, se necessário (na primeira execução ou atualização de configuração)
3. Dividir o texto em frases usando NLTK
4. Pesquisar no armazenamento vetorial FAISS para encontrar conceitos de ontologia relevantes
5. Construir subconjunto de ontologia com inclusão automática de propriedades
6. Construir variáveis de prompt com modelo Jinja2
7. Chamar o serviço de prompt com o modelo extract-with-ontologies
8. Analisar a resposta JSON em triplas estruturadas
9. Validar as triplas e expandir os URIs para URIs completos da ontologia
10. Gerar triplas de definição de ontologia (classes e propriedades com rótulos/comentários/domínios/intervalos)
11. Construir contextos de entidade a partir de todas as triplas
12. Emitir para as filas de triplas e contextos de entidade

**Características Principais**:
Armazenamentos vetoriais específicos para cada fluxo, suportando diferentes modelos de incorporação
Atualizações de ontologia orientadas por eventos via fila config-update
Expansão automática de URIs usando URIs de ontologia
Elementos de ontologia adicionados ao grafo de conhecimento com metadados completos
Contextos de entidade incluem elementos de conteúdo e de ontologia

**Localização da Implementação**: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`

### Configuração

O serviço usa a abordagem de configuração padrão da TrustGraph com argumentos de linha de comando:

```bash
kg-extract-ontology \
  --id kg-extract-ontology \
  --pulsar-host localhost:6650 \
  --input-queue chunks \
  --config-input-queue config-update \
  --output-queue triples \
  --entity-contexts-output-queue entity-contexts
```

**Parâmetros de Configuração Chave**:
`similarity_threshold`: 0.3 (padrão, configurável no código)
`top_k`: 10 (número de elementos de ontologia a serem recuperados por segmento)
`vector_store`: Per-flow FAISS IndexFlatIP com dimensões detectadas automaticamente
`text_processor`: NLTK com tokenização de frases punkt_tab
`prompt_template`: "extract-with-ontologies" (template Jinja2)

**Configuração da Ontologia**:
As ontologias são carregadas dinamicamente através da fila de atualização de configuração com o tipo "ontology".

### Fluxo de Dados

1. **Fase de Inicialização** (por fluxo):
   Receber configuração da ontologia através da fila de atualização de configuração
   Analisar o JSON da ontologia em objetos OntologyClass e OntologyProperty
   Gerar embeddings para todos os elementos da ontologia usando EmbeddingsClientSpec
   Armazenar embeddings no armazenamento vetorial FAISS específico do fluxo
   Detectar automaticamente as dimensões do embedding a partir da primeira resposta

2. **Fase de Extração** (por chunk):
   Receber um chunk da fila chunks-input
   Dividir o chunk em frases usando NLTK
   Calcular embeddings para cada frase
   Pesquisar no armazenamento vetorial FAISS por elementos de ontologia relevantes
   Construir um subconjunto de ontologia com inclusão automática de propriedades
   Construir variáveis de template Jinja2 com texto e ontologia
   Chamar o serviço de prompt com o template extract-with-ontologies
   Analisar a resposta JSON e validar as triplas
   Expandir URIs usando URIs da ontologia
   Gerar triplas de definição de ontologia
   Construir contextos de entidade a partir de todas as triplas
   Emitir para as filas de triplas e entity-contexts

### Armazenamento Vetorial em Memória

**Propósito**: Fornece uma pesquisa de similaridade rápida e baseada em memória para correspondência de elementos de ontologia.

**Implementação: FAISS**

O sistema usa **FAISS (Facebook AI Similarity Search)** com IndexFlatIP para pesquisa de similaridade de cosseno exata. Características principais:

**IndexFlatIP**: Pesquisa de similaridade de cosseno exata usando produto interno
**Detecção automática**: Dimensão determinada a partir da primeira resposta de embedding
**Armazenamentos per-flow**: Cada fluxo tem um armazenamento vetorial independente para diferentes modelos de embedding
**Normalização**: Todos os vetores normalizados antes da indexação
**Operações em lote**: Adição em lote eficiente para o carregamento inicial da ontologia

**Localização da Implementação**: `trustgraph-flow/trustgraph/extract/kg/ontology/vector_store.py`

### Algoritmo de Seleção de Subconjunto de Ontologia

**Propósito**: Seleciona dinamicamente a porção relevante mínima da ontologia para cada chunk de texto.

**Etapas Detalhadas do Algoritmo**:

1. **Segmentação de Texto**:
   Dividir o chunk de entrada em frases usando detecção de frases NLP
   Extrair frases nominais, frases verbais e entidades nomeadas de cada frase
   Criar uma estrutura hierárquica de segmentos preservando o contexto

2. **Geração de Embedding**:
   Gerar embeddings vetoriais para cada segmento de texto (frases e frases)
   Usar o mesmo modelo de embedding usado para elementos de ontologia
   Armazenar em cache os embeddings para segmentos repetidos para melhorar o desempenho

3. **Pesquisa de Similaridade**:
   Para cada embedding de segmento de texto, pesquisar no armazenamento vetorial
   Recuperar os k (por exemplo, 10) elementos de ontologia mais similares
   Aplicar um limite de similaridade (por exemplo, 0,7) para filtrar correspondências fracas
   Agregar os resultados em todos os segmentos, rastreando as frequências de correspondência

4. **Resolução de Dependências**:
   Para cada classe selecionada, incluir recursivamente todas as classes pai até a raiz
   Para cada propriedade selecionada, incluir suas classes de domínio e intervalo
   Para propriedades inversas, garantir que ambas as direções sejam incluídas
   Adicionar classes equivalentes se existirem na ontologia

5. **Construção de Subconjunto**:
   Desduplicar os elementos coletados, preservando os relacionamentos
   Organizar em classes, propriedades de objeto e propriedades de tipo de dados
   Garantir que todas as restrições e relacionamentos sejam preservados
   Criar uma mini-ontologia autocontida que seja válida e completa

**Exemplo de Demonstração**:
Dado o texto: "The brown dog chased the white cat up the tree."
Segmentos: ["brown dog", "white cat", "tree", "chased"]
Elementos correspondidos: [dog (class), cat (class), animal (parent), chases (property)]
Dependências: [animal (parent of dog and cat), lifeform (parent of animal)]
Subconjunto final: Mini-ontologia completa com hierarquia animal e relação de perseguição

### Validação de Triplas

**Propósito**: Garante que todas as triplas extraídas estejam estritamente em conformidade com as restrições da ontologia.

**Algoritmo de Validação**:
Após a última linha traduzida, insira uma linha final contendo exatamente: [[__END_OF_TRANSLATION__]]
1. **Validação de Classe**:
   Verificar se os sujeitos são instâncias de classes definidas no subconjunto da ontologia
   Para propriedades de objeto, verificar se os objetos também são instâncias de classes válidas
   Verificar os nomes das classes em relação ao dicionário de classes da ontologia
   Lidar com hierarquias de classes - instâncias de subclasses são válidas para restrições da classe pai

2. **Validação de Propriedade**:
   Confirmar se os predicados correspondem a propriedades no subconjunto da ontologia
   Distinguir entre propriedades de objeto (entidade-para-entidade) e propriedades de tipo de dado (entidade-para-literal)
   Verificar se os nomes das propriedades correspondem exatamente (considerando o namespace, se presente)

3. **Verificação de Domínio/Intervalo**:
   Para cada propriedade usada como predicado, recuperar seu domínio e intervalo
   Verificar se o tipo do sujeito corresponde ou herda do domínio da propriedade
   Verificar se o tipo do objeto corresponde ou herda do intervalo da propriedade
   Para propriedades de tipo de dado, verificar se o objeto é um literal do tipo XSD correto

4. **Validação de Cardinalidade**:
   Monitorar a contagem de uso da propriedade por sujeito
   Verificar a cardinalidade mínima - garantir que as propriedades obrigatórias estejam presentes
   Verificar a cardinalidade máxima - garantir que a propriedade não seja usada muitas vezes
   Para propriedades funcionais, garantir que haja no máximo um valor por sujeito

5. **Validação de Tipo de Dado**:
   Analisar os valores literais de acordo com seus tipos XSD declarados
   Validar se os inteiros são números válidos, se as datas estão formatadas corretamente, etc.
   Verificar padrões de string se restrições de regex forem definidas
   Garantir que os URIs sejam bem formados para tipos xsd:anyURI

**Exemplo de Validação**:
Tripla: ("Buddy", "has-owner", "John")
Verificar se "Buddy" é tipado como uma classe que pode ter a propriedade "has-owner"
Verificar se "has-owner" existe na ontologia
Verificar a restrição de domínio: o sujeito deve ser do tipo "Pet" ou subclasse
Verificar a restrição de intervalo: o objeto deve ser do tipo "Person" ou subclasse
Se válido, adicionar à saída; se inválido, registrar a violação e pular

## Considerações de Desempenho

### Estratégias de Otimização

1. **Cache de Incorporações**: Armazenar em cache as incorporações para segmentos de texto frequentemente usados
2. **Processamento em Lote**: Processar vários segmentos em paralelo
3. **Indexação de Armazenamento Vetorial**: Usar algoritmos de vizinhos mais próximos aproximados para ontologias grandes
4. **Otimização de Prompt**: Minimizar o tamanho do prompt incluindo apenas os elementos essenciais da ontologia
5. **Cache de Resultados**: Armazenar em cache os resultados da extração para trechos idênticos

### Escalabilidade

**Escalabilidade Horizontal**: Múltiplas instâncias do extrator com cache de ontologia compartilhado
**Particionamento da Ontologia**: Dividir ontologias grandes por domínio
**Processamento em Streaming**: Processar trechos à medida que chegam, sem agrupamento
**Gerenciamento de Memória**: Limpeza periódica de incorporações não utilizadas

## Tratamento de Erros

### Cenários de Falha

1. **Ontologias Ausentes**: Recuar para a extração sem restrições
2. **Falha do Serviço de Incorporação**: Usar incorporações armazenadas em cache ou pular a correspondência semântica
3. **Tempo Limite do Serviço de Prompt**: Tentar novamente com retrocesso exponencial
4. **Formato de Tripla Inválido**: Registrar e pular triplas mal formadas
5. **Inconsistências na Ontologia**: Relatar conflitos e usar os elementos válidos mais específicos

### Monitoramento

Métricas-chave a serem monitoradas:

Tempo de carregamento da ontologia e uso de memória
Latência de geração de incorporação
Desempenho da pesquisa vetorial
Tempo de resposta do serviço de prompt
Precisão da extração de triplas
Taxa de conformidade da ontologia

## Caminho de Migração

### De Extratores Existentes

1. **Operação Paralela**: Executar em paralelo com os extratores existentes inicialmente
2. **Implantação Gradual**: Começar com tipos específicos de documentos
3. **Comparação de Qualidade**: Comparar a qualidade da saída com os extratores existentes
4. **Migração Completa**: Substituir os extratores existentes assim que a qualidade for verificada

### Desenvolvimento de Ontologia

1. **Inicialização a partir do Existente**: Gerar ontologias iniciais a partir do conhecimento existente
2. **Refinamento Iterativo**: Refinar com base em padrões de extração
3. **Revisão por Especialistas no Domínio**: Validar com especialistas no assunto
4. **Melhoria Contínua**: Atualizar com base no feedback da extração

## Serviço de Consulta Sensível à Ontologia

### Visão Geral

O serviço de consulta sensível à ontologia fornece múltiplos caminhos de consulta para suportar diferentes armazenamentos de grafos de back-end. Ele aproveita o conhecimento da ontologia para um questionamento preciso e semanticamente consciente em diferentes armazenamentos de grafos, tanto Cassandra (via SPARQL) quanto armazenamentos de grafos baseados em Cypher (Neo4j, Memgraph, FalkorDB).

**Componentes do Serviço**:
`onto-query-sparql`: Converte linguagem natural para SPARQL para Cassandra
`sparql-cassandra`: Camada de consulta SPARQL para Cassandra usando rdflib
`onto-query-cypher`: Converte linguagem natural para Cypher para bancos de dados de grafos
`cypher-executor`: Execução de consulta Cypher para Neo4j/Memgraph/FalkorDB

### Arquitetura

```
                    ┌─────────────────┐
                    │   User Query    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │   Question      │────▶│   Sentence   │
                    │   Analyser      │      │   Splitter   │
                    └────────┬────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │   Ontology      │────▶│   Vector     │
                    │   Matcher       │      │    Store     │
                    └────────┬────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Backend Router  │
                    └────────┬────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ onto-query-     │          │ onto-query-     │
    │    sparql       │          │    cypher       │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   SPARQL        │          │   Cypher        │
    │  Generator      │          │  Generator      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ sparql-         │          │ cypher-         │
    │ cassandra       │          │ executor        │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   Cassandra     │          │ Neo4j/Memgraph/ │
    │                 │          │   FalkorDB      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             └────────────┬───────────────┘
                          │
                          ▼
                 ┌─────────────────┐      ┌──────────────┐
                 │   Answer        │────▶│   Prompt     │
                 │  Generator      │      │   Service    │
                 └────────┬────────┘      └──────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Final Answer   │
                 └─────────────────┘
```

### Processamento de Consultas

#### 1. Analisador de Perguntas

**Propósito**: Decompõe as perguntas do usuário em componentes semânticos para correspondência com a ontologia.

**Descrição do Algoritmo**:
O Analisador de Perguntas recebe a pergunta em linguagem natural e a divide em segmentos significativos, utilizando a mesma abordagem de divisão de frases utilizada no pipeline de extração. Ele identifica entidades, relacionamentos e restrições importantes mencionadas na pergunta. Cada segmento é analisado para determinar o tipo de pergunta (factual, agregação, comparação, etc.) e o formato de resposta esperado. Essa decomposição ajuda a identificar quais partes da ontologia são mais relevantes para responder à pergunta.

**Operações Principais**:
Dividir a pergunta em frases e expressões
Identificar o tipo e a intenção da pergunta
Extrair entidades e relacionamentos mencionados
Detectar restrições e filtros na pergunta
Determinar o formato de resposta esperado

#### 2. Correspondência de Ontologia para Consultas

**Propósito**: Identifica o subconjunto relevante da ontologia necessário para responder à pergunta.

**Descrição do Algoritmo**:
Similar ao Seletor de Ontologia do pipeline de extração, mas otimizado para responder a perguntas. O correspondente gera incorporações para segmentos de perguntas e pesquisa no armazenamento vetorial por elementos relevantes da ontologia. No entanto, ele se concentra em encontrar conceitos que seriam úteis para a construção de consultas, em vez de extração. Ele expande a seleção para incluir propriedades relacionadas que podem ser percorridas durante a exploração do grafo, mesmo que não sejam explicitamente mencionadas na pergunta. Por exemplo, se for feita uma pergunta sobre "funcionários", ele pode incluir propriedades como "trabalha-para", "gerencia" e "reporta-a", que podem ser relevantes para encontrar informações sobre funcionários.

**Estratégia de Correspondência**:
Gerar incorporações para segmentos de perguntas
Encontrar conceitos da ontologia diretamente mencionados
Incluir propriedades que conectam classes mencionadas
Adicionar propriedades inversas e relacionadas para travessia
Incluir classes pai/filho para consultas hierárquicas
Construir uma partição da ontologia focada na consulta

#### 3. Roteador de Backend

**Propósito**: Roteia as consultas para o caminho de consulta específico do backend apropriado, com base na configuração.

**Descrição do Algoritmo**:
O Roteador de Backend examina a configuração do sistema para determinar qual backend de grafo está ativo (Cassandra ou baseado em Cypher). Ele roteia a pergunta e a partição da ontologia para o serviço de geração de consulta apropriado. O roteador também pode suportar balanceamento de carga entre vários backends ou mecanismos de fallback se o backend primário estiver indisponível.

**Lógica de Roteamento**:
Verificar o tipo de backend configurado nas configurações do sistema
Rotear para `onto-query-sparql` para backends Cassandra
Rotear para `onto-query-cypher` para Neo4j/Memgraph/FalkorDB
Suportar configurações multi-backend com distribuição de consultas
Lidar com cenários de failover e balanceamento de carga

#### 4. Geração de Consulta SPARQL (`onto-query-sparql`)

**Propósito**: Converte perguntas em linguagem natural em consultas SPARQL para execução no Cassandra.

**Descrição do Algoritmo**:
O gerador de consulta SPARQL recebe a pergunta e a partição da ontologia e constrói uma consulta SPARQL otimizada para execução no backend Cassandra. Ele usa o serviço de prompt com um modelo específico para SPARQL que inclui semântica RDF/OWL. O gerador entende padrões SPARQL como caminhos de propriedade, cláusulas opcionais e filtros que podem ser traduzidos de forma eficiente em operações do Cassandra.

**Modelo de Prompt de Geração SPARQL**:
```
Generate a SPARQL query for the following question using the provided ontology.

ONTOLOGY CLASSES:
{classes}

ONTOLOGY PROPERTIES:
{properties}

RULES:
- Use proper RDF/OWL semantics
- Include relevant prefixes
- Use property paths for hierarchical queries
- Add FILTER clauses for constraints
- Optimise for Cassandra backend

QUESTION: {question}

SPARQL QUERY:
```

#### 5. Geração de Consultas Cypher (`onto-query-cypher`)

**Propósito**: Converte perguntas em linguagem natural em consultas Cypher para bancos de dados de grafos.

**Descrição do Algoritmo**:
O gerador de consultas Cypher cria consultas Cypher nativas otimizadas para Neo4j, Memgraph e FalkorDB. Ele mapeia classes de ontologia para rótulos de nós e propriedades para relacionamentos, usando a sintaxe de correspondência de padrões do Cypher. O gerador inclui otimizações específicas do Cypher, como dicas de direção de relacionamento, uso de índices e dicas de planejamento de consulta.

**Modelo de Prompt de Geração Cypher**:
```
Generate a Cypher query for the following question using the provided ontology.

NODE LABELS (from classes):
{classes}

RELATIONSHIP TYPES (from properties):
{properties}

RULES:
- Use MATCH patterns for graph traversal
- Include WHERE clauses for filters
- Use aggregation functions when needed
- Optimise for graph database performance
- Consider index hints for large datasets

QUESTION: {question}

CYPHER QUERY:
```

#### 6. Motor de Consulta SPARQL-Cassandra (`sparql-cassandra`)

**Propósito**: Executa consultas SPARQL contra o Cassandra usando Python rdflib.

**Descrição do Algoritmo**:
O motor SPARQL-Cassandra implementa um processador SPARQL usando a biblioteca rdflib do Python com um armazenamento backend personalizado para o Cassandra. Ele traduz padrões de grafos SPARQL em consultas CQL apropriadas para o Cassandra, tratando junções, filtros e agregações. O motor mantém um mapeamento RDF para Cassandra que preserva a estrutura semântica, otimizando para o modelo de armazenamento de famílias de colunas do Cassandra.

**Características da Implementação**:
Implementação da interface de armazenamento rdflib para o Cassandra
Suporte para consultas SPARQL 1.1 com padrões comuns
Tradução eficiente de padrões de triplas para CQL
Suporte para caminhos de propriedades e consultas hierárquicas
Streaming de resultados para grandes conjuntos de dados
Pool de conexões e cache de consultas

**Exemplo de Tradução**:
```sparql
SELECT ?animal WHERE {
  ?animal rdf:type :Animal .
  ?animal :hasOwner "John" .
}
```
Traduz para consultas otimizadas do Cassandra, utilizando índices e chaves de partição.

#### 7. Executor de Consultas Cypher (`cypher-executor`)

**Propósito**: Executa consultas Cypher contra Neo4j, Memgraph e FalkorDB.

**Descrição do Algoritmo**:
O executor de consultas Cypher fornece uma interface unificada para executar consultas Cypher em diferentes bancos de dados de grafos. Ele gerencia protocolos de conexão específicos do banco de dados, dicas de otimização de consultas e normalização do formato de resultados. O executor inclui lógica de repetição, pool de conexões e gerenciamento de transações adequados para cada tipo de banco de dados.

**Suporte a Múltiplos Bancos de Dados**:
**Neo4j**: Protocolo Bolt, funções de transação, dicas de índice
**Memgraph**: Protocolo personalizado, resultados de streaming, consultas analíticas
**FalkorDB**: Adaptação do protocolo Redis, otimizações em memória

**Recursos de Execução**:
Gerenciamento de conexão independente do banco de dados
Validação de consulta e verificação de sintaxe
Imposição de tempo limite e limites de recursos
Paginação e streaming de resultados
Monitoramento de desempenho por tipo de banco de dados
Failover automático entre instâncias de banco de dados

#### 8. Gerador de Respostas

**Propósito**: Sintetiza uma resposta em linguagem natural a partir dos resultados da consulta.

**Descrição do Algoritmo**:
O Gerador de Respostas recebe os resultados estruturados da consulta e a pergunta original, e então usa o serviço de prompt para gerar uma resposta abrangente. Ao contrário de respostas simples baseadas em modelos, ele usa um LLM para interpretar os dados do grafo no contexto da pergunta, lidando com relacionamentos complexos, agregações e inferências. O gerador pode explicar seu raciocínio referenciando a estrutura da ontologia e os triplos específicos recuperados do grafo.

**Processo de Geração de Respostas**:
Formata os resultados da consulta em um contexto estruturado
Inclui definições de ontologia relevantes para maior clareza
Constrói um prompt com a pergunta e os resultados
Gera uma resposta em linguagem natural por meio de um LLM
Valida a resposta em relação à intenção da consulta
Adiciona citações a entidades específicas do grafo, se necessário

### Integração com Serviços Existentes

#### Relação com GraphRAG

**Complementar**: onto-query fornece precisão semântica, enquanto GraphRAG fornece ampla cobertura
**Infraestrutura Compartilhada**: Ambos usam o mesmo grafo de conhecimento e serviços de prompt
**Roteamento de Consultas**: O sistema pode rotear consultas para o serviço mais apropriado com base no tipo de pergunta
**Modo Híbrido**: Pode combinar ambas as abordagens para respostas abrangentes

#### Relação com OntoRAG Extraction

**Ontologias Compartilhadas**: Usa as mesmas configurações de ontologia carregadas por kg-extract-ontology
**Vector Store Compartilhado**: Reutiliza os embeddings na memória do serviço de extração
**Semântica Consistente**: As consultas operam em grafos construídos com as mesmas restrições ontológicas

### Exemplos de Consultas

#### Exemplo 1: Consulta Simples de Entidade
**Pergunta**: "Quais animais são mamíferos?"
**Correspondência de Ontologia**: [animal, mammal, subClassOf]
**Consulta Gerada**:
```cypher
MATCH (a:animal)-[:subClassOf*]->(m:mammal)
RETURN a.name
```

#### Exemplo 2: Consulta de Relacionamento
**Pergunta**: "Quais documentos foram escritos por John Smith?"
**Correspondência com a Ontologia**: [documento, pessoa, tem-autor]
**Consulta Gerada**:
```cypher
MATCH (d:document)-[:has-author]->(p:person {name: "John Smith"})
RETURN d.title, d.date
```

#### Exemplo 3: Consulta de Agregação
**Pergunta**: "Quantas patas têm os gatos?"
**Correspondência com a Ontologia**: [gato, número-de-patas (propriedade de tipo de dado)]
**Consulta Gerada**:
```cypher
MATCH (c:cat)
RETURN c.name, c.number_of_legs
```

### Configuração

```yaml
onto-query:
  embedding_model: "text-embedding-3-small"
  vector_store:
    shared_with_extractor: true  # Reuse kg-extract-ontology's store
  query_builder:
    model: "gpt-4"
    temperature: 0.1
    max_query_length: 1000
  graph_executor:
    timeout: 30000  # ms
    max_results: 1000
  answer_generator:
    model: "gpt-4"
    temperature: 0.3
    max_tokens: 500
```

### Otimizações de Desempenho

#### Otimização de Consultas

**Poda da Ontologia**: Inclua apenas os elementos da ontologia necessários nos prompts.
**Cache de Consultas**: Armazene em cache as perguntas e consultas frequentemente feitas.
**Cache de Resultados**: Armazene os resultados para consultas idênticas dentro de um período de tempo.
**Processamento em Lote**: Processe várias perguntas relacionadas em uma única travessia de grafo.

#### Considerações de Escalabilidade

**Execução Distribuída**: Paralelize subconsultas em partições do grafo.
**Resultados Incrementais**: Transmita os resultados para conjuntos de dados grandes.
**Balanceamento de Carga**: Distribua a carga de consulta entre várias instâncias de serviço.
**Piscina de Recursos**: Gerencie as piscinas de conexão para bancos de dados de grafo.

### Tratamento de Erros

#### Cenários de Falha

1. **Geração de Consulta Inválida**: Utilize o GraphRAG ou a pesquisa por palavras-chave.
2. **Incompatibilidade da Ontologia**: Expanda a pesquisa para um subconjunto mais amplo da ontologia.
3. **Tempo Limite da Consulta**: Simplifique a consulta ou aumente o tempo limite.
4. **Resultados Vazios**: Sugira a reformulação da consulta ou perguntas relacionadas.
5. **Falha do Serviço LLM**: Utilize consultas armazenadas em cache ou respostas baseadas em modelos.

### Métricas de Monitoramento

Distribuição da complexidade das perguntas.
Tamanhos das partições da ontologia.
Taxa de sucesso na geração de consultas.
Tempo de execução da consulta do grafo.
Pontuações de qualidade da resposta.
Taxas de acerto do cache.
Frequências de erro por tipo.

## Melhorias Futuras

1. **Aprendizado da Ontologia**: Estenda automaticamente as ontologias com base em padrões de extração.
2. **Pontuação de Confiança**: Atribua pontuações de confiança às triplas extraídas.
3. **Geração de Explicação**: Forneça o raciocínio para a extração de triplas.
4. **Aprendizado Ativo**: Solicite validação humana para extrações incertas.

## Considerações de Segurança

1. **Prevenção de Injeção de Prompt**: Limpe o texto do chunk antes da construção do prompt.
2. **Limites de Recursos**: Defina um limite para o uso de memória para o armazenamento vetorial.
3. **Limitação de Taxa**: Limite as solicitações de extração por cliente.
4. **Registro de Auditoria**: Rastreie todas as solicitações e resultados de extração.

## Estratégia de Teste

### Teste Unitário

Carregador de ontologia com vários formatos.
Geração e armazenamento de incorporações.
Algoritmos de divisão de frases.
Cálculos de similaridade vetorial.
Análise e validação de triplas.

### Teste de Integração

Pipeline de extração de ponta a ponta.
Integração do serviço de configuração.
Interação com o serviço de prompt.
Tratamento de extração concorrente.

### Teste de Desempenho

Tratamento de ontologias grandes (1000+ classes).
Processamento de alto volume de chunks.
Uso de memória sob carga.
Benchmarks de latência.

## Plano de Entrega

### Visão Geral

O sistema OntoRAG será entregue em quatro fases principais, com cada fase fornecendo valor incremental, construindo em direção ao sistema completo. O plano se concentra em estabelecer as capacidades básicas de extração primeiro, depois adicionando funcionalidade de consulta, seguido por otimizações e recursos avançados.

### Fase 1: Fundação e Extração Central

**Objetivo**: Estabelecer o pipeline básico de extração orientado à ontologia com correspondência vetorial simples.

#### Etapa 1.1: Fundação do Gerenciamento de Ontologia
Implementar o carregador de configuração da ontologia (`OntologyLoader`).
Analisar e validar estruturas JSON da ontologia.
Criar armazenamento de ontologia na memória e padrões de acesso.
Implementar o mecanismo de atualização da ontologia.

**Critérios de Sucesso**:
Carregar e analisar com sucesso as configurações da ontologia.
Validar a estrutura e a consistência da ontologia.
Lidar com várias ontologias simultâneas.

#### Etapa 1.2: Implementação do Armazenamento Vetorial
Implementar um armazenamento vetorial simples baseado em NumPy como um protótipo inicial.
Adicionar a implementação do armazenamento vetorial FAISS.
Criar uma abstração de interface de armazenamento vetorial.
Implementar a pesquisa de similaridade com limites configuráveis.

**Critérios de Sucesso**:
Armazenar e recuperar embeddings de forma eficiente
Realizar busca de similaridade com latência inferior a 100ms
Suportar backends NumPy e FAISS

#### Etapa 1.3: Pipeline de Embedding de Ontologia
Integrar com o serviço de embedding
Implementar componente `OntologyEmbedder`
Gerar embeddings para todos os elementos da ontologia
Armazenar embeddings com metadados no armazenamento vetorial

**Critérios de Sucesso**:
Gerar embeddings para classes e propriedades
Armazenar embeddings com metadados adequados
Reconstruir embeddings em caso de atualizações da ontologia

#### Etapa 1.4: Componentes de Processamento de Texto
Implementar separador de frases usando NLTK/spaCy
Extrair frases e entidades nomeadas
Criar hierarquia de segmentos de texto
Gerar embeddings para segmentos de texto

**Critérios de Sucesso**:
Dividir o texto em frases com precisão
Extrair frases significativas
Manter as relações de contexto

#### Etapa 1.5: Algoritmo de Seleção de Ontologia
Implementar correspondência de similaridade entre texto e ontologia
Criar resolução de dependências para elementos da ontologia
Criar subconjuntos coerentes mínimos da ontologia
Otimizar o desempenho da geração de subconjuntos

**Critérios de Sucesso**:
Selecionar elementos relevantes da ontologia com precisão >80%
Incluir todas as dependências necessárias
Gerar subconjuntos em <500ms

#### Etapa 1.6: Serviço Básico de Extração
Implementar construção de prompts para extração
Integrar com o serviço de prompts
Analisar e validar respostas de triplas
Criar endpoint de serviço `kg-extract-ontology`

**Critérios de Sucesso**:
Extrair triplas conformes à ontologia
Validar todas as triplas em relação à ontologia
Lidar com erros de extração de forma elegante

### Fase 2: Implementação do Sistema de Consulta

**Objetivo**: Adicionar capacidades de consulta com conhecimento da ontologia, com suporte para vários backends.

#### Etapa 2.1: Componentes Fundamentais da Consulta
Implementar analisador de perguntas
Criar correspondência de ontologia para consultas
Adaptar a busca vetorial para o contexto da consulta
Construir componente de roteamento de backend

**Critérios de Sucesso**:
Analisar perguntas em componentes semânticos
Corresponder perguntas a elementos relevantes da ontologia
Rotear consultas para o backend apropriado

#### Etapa 2.2: Implementação do Caminho SPARQL
Implementar serviço `onto-query-sparql`
Criar gerador de consultas SPARQL usando LLM
Desenvolver modelos de prompt para geração de SPARQL
Validar a sintaxe SPARQL gerada

**Critérios de Sucesso**:
Gerar consultas SPARQL válidas
Usar padrões SPARQL apropriados
Lidar com tipos de consulta complexos

#### Etapa 2.3: Motor SPARQL-Cassandra
Implementar interface de armazenamento rdflib para Cassandra
Criar tradutor de consultas CQL
Otimizar a correspondência de padrões de triplas
Lidar com a formatação de resultados SPARQL

**Critérios de Sucesso**:
Executar consultas SPARQL no Cassandra
Suportar padrões SPARQL comuns
Retornar resultados em formato padrão

#### Etapa 2.4: Implementação do Caminho Cypher
Implementar serviço `onto-query-cypher`
Criar gerador de consultas Cypher usando LLM
Desenvolver modelos de prompt para geração de Cypher
Validar a sintaxe Cypher gerada

**Critérios de Sucesso**:
Gerar consultas Cypher válidas
Usar padrões de grafo apropriados
Suportar Neo4j, Memgraph, FalkorDB

#### Etapa 2.5: Executor Cypher
Implementar executor Cypher multi-banco de dados
Suportar protocolo Bolt (Neo4j/Memgraph)
Suportar protocolo Redis (FalkorDB)
Lidar com a normalização de resultados

**Critérios de Sucesso**:
Executar Cypher em todos os bancos de dados alvo
Lidar com diferenças específicas de cada banco de dados
Manter pools de conexão de forma eficiente

#### Etapa 2.6: Geração de Respostas
Implementar componente de gerador de respostas
Criar prompts para síntese de respostas
Formatar resultados de consulta para consumo por LLM
Gerar respostas em linguagem natural

**Critérios de Sucesso**:
Gerar respostas precisas a partir de resultados de consulta
Manter o contexto da pergunta original
Fornecer respostas claras e concisas

### Fase 3: Otimização e Robustez

**Objetivo**: Otimizar o desempenho, adicionar cache, melhorar o tratamento de erros e aumentar a confiabilidade.

#### Etapa 3.1: Otimização de Desempenho
Implementar cache de embeddings
Adicionar cache de resultados de consulta
Otimizar a busca vetorial com índices FAISS IVF
Implementar processamento em lote para embeddings

**Critérios de Sucesso**:
Reduzir a latência média da consulta em 50%
Suportar 10 vezes mais requisições simultâneas
Manter tempos de resposta abaixo de um segundo

#### Etapa 3.2: Tratamento Avançado de Erros
Implementar recuperação abrangente de erros
Adicionar mecanismos de fallback entre caminhos de consulta
Criar lógica de repetição com retrocesso exponencial
Melhorar o registro e o diagnóstico de erros

**Critérios de Sucesso**:
Lidar graciosamente com todos os cenários de falha
Failover automático entre backends
Relatório de erros detalhado para depuração

#### Etapa 3.3: Monitoramento e Observabilidade
Adicionar coleta de métricas de desempenho
Implementar rastreamento de consultas
Criar endpoints de verificação de saúde
Adicionar monitoramento de uso de recursos

**Critérios de Sucesso**:
Rastrear todos os indicadores de desempenho chave
Identificar gargalos rapidamente
Monitorar a saúde do sistema em tempo real

#### Etapa 3.4: Gerenciamento de Configuração
Implementar atualizações dinâmicas de configuração
Adicionar validação de configuração
Criar modelos de configuração
Suportar configurações específicas do ambiente

**Critérios de Sucesso**:
Atualizar a configuração sem reinicialização
Validar todas as alterações de configuração
Suportar múltiplos ambientes de implantação

### Fase 4: Recursos Avançados

**Objetivo**: Adicionar capacidades sofisticadas para implantação em produção e funcionalidade aprimorada.

#### Etapa 4.1: Suporte a Múltiplas Ontologias
Implementar lógica de seleção de ontologia
Suportar consultas entre ontologias
Lidar com versionamento de ontologias
Criar capacidades de mesclagem de ontologias

**Critérios de Sucesso**:
Consultar em múltiplas ontologias
Lidar com conflitos de ontologia
Suportar a evolução da ontologia

#### Etapa 4.2: Roteamento Inteligente de Consultas
Implementar roteamento baseado em desempenho
Adicionar análise de complexidade de consulta
Criar algoritmos de roteamento adaptativos
Suportar testes A/B para caminhos

**Critérios de Sucesso**:
Roteamento de consultas de forma otimizada
Aprendizado com o desempenho das consultas
Melhoria do roteamento ao longo do tempo

#### Etapa 4.3: Recursos Avançados de Extração
Adicionar pontuação de confiança para triplas
Implementar geração de explicações
Criar loops de feedback para melhoria
Suportar aprendizado incremental

**Critérios de Sucesso**:
Fornecer pontuações de confiança
Explicar decisões de extração
Melhorar continuamente a precisão

#### Etapa 4.4: Endurecimento para Produção
Adicionar limitação de taxa
Implementar autenticação/autorização
Criar automação de implantação
Adicionar backup e recuperação

**Critérios de Sucesso**:
Segurança pronta para produção
Pipeline de implantação automatizado
Capacidade de recuperação de desastres

### Marcos de Entrega

1. **Marco 1** (Fim da Fase 1): Extração básica orientada por ontologia operacional
2. **Marco 2** (Fim da Fase 2): Sistema de consulta completo com caminhos SPARQL e Cypher
3. **Marco 3** (Fim da Fase 3): Sistema otimizado e robusto pronto para o ambiente de testes
4. **Marco 4** (Fim da Fase 4): Sistema pronto para produção com recursos avançados

### Mitigação de Riscos

#### Riscos Técnicos
**Escalabilidade do Vector Store**: Começar com NumPy, migrar gradualmente para FAISS
**Precisão da Geração de Consultas**: Implementar mecanismos de validação e fallback
**Compatibilidade com o Backend**: Testar extensivamente com cada tipo de banco de dados
**Gargalos de Desempenho**: Analisar o desempenho frequentemente e otimizar iterativamente

#### Riscos Operacionais
**Qualidade da Ontologia**: Implementar validação e verificação de consistência
**Dependências de Serviço**: Adicionar circuit breakers e fallbacks
**Restrições de Recursos**: Monitorar e definir limites apropriados
**Consistência de Dados**: Implementar tratamento de transações adequado

### Métricas de Sucesso

#### Métricas de Sucesso da Fase 1
Precisão da extração: >90% de conformidade com a ontologia
Velocidade de processamento: <1 segundo por chunk
Tempo de carregamento da ontologia: <10 segundos
Latência da busca vetorial: <100ms

#### Métricas de Sucesso da Fase 2
Taxa de sucesso da consulta: >95%
Latência da consulta: <2 segundos de ponta a ponta
Compatibilidade com o backend: 100% para bancos de dados de destino
Precisão da resposta: >85% com base nos dados disponíveis

#### Métricas de Sucesso da Fase 3
Tempo de atividade do sistema: >99,9%
Taxa de recuperação de erros: >95%
Taxa de acerto em cache: >60%
Usuários simultâneos: >100

#### Métricas de Sucesso da Fase 4
Consultas multi-ontologia: Totalmente suportadas
Otimização de roteamento: Redução de latência de 30%
Precisão da pontuação de confiança: >90%
Implantação em produção: Atualizações sem interrupção

## Referências

[OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
[GraphRAG Architecture](https://github.com/microsoft/graphrag)
[Sentence Transformers](https://www.sbert.net/)
[FAISS Vector Search](https://github.com/facebookresearch/faiss)
[spaCy NLP Library](https://spacy.io/)
[rdflib Documentation](https://rdflib.readthedocs.io/)
[Neo4j Bolt Protocol](https://neo4j.com/docs/bolt/current/)
