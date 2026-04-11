# Especificação Técnica de Dados Estruturados

## Visão Geral

Esta especificação descreve a integração do TrustGraph com fluxos de dados estruturados, permitindo que o sistema trabalhe com dados que podem ser representados como linhas em tabelas ou objetos em armazenamentos de objetos. A integração suporta quatro casos de uso primários:

1. **Extração de Não Estruturado para Estruturado**: Ler fontes de dados não estruturados, identificar e extrair estruturas de objetos e armazená-las em um formato tabular.
2. **Ingestão de Dados Estruturados**: Carregar dados que já estão em formatos estruturados diretamente no armazenamento estruturado, juntamente com os dados extraídos.
3. **Consulta em Linguagem Natural**: Converter perguntas em linguagem natural em consultas estruturadas para extrair dados correspondentes do armazenamento.
4. **Consulta Estruturada Direta**: Executar consultas estruturadas diretamente contra o armazenamento de dados para recuperação precisa de dados.

## Objetivos

**Acesso Unificado a Dados**: Fornecer uma única interface para acessar dados estruturados e não estruturados dentro do TrustGraph.
**Integração Perfeita**: Permitir interoperabilidade perfeita entre a representação de conhecimento baseada em grafo do TrustGraph e formatos de dados estruturados tradicionais.
**Extração Flexível**: Suportar a extração automática de dados estruturados de várias fontes não estruturadas (documentos, texto, etc.).
**Versatilidade de Consulta**: Permitir que os usuários consultem dados usando linguagem natural e linguagens de consulta estruturadas.
**Consistência de Dados**: Manter a integridade e a consistência dos dados em diferentes representações de dados.
**Otimização de Desempenho**: Garantir o armazenamento e a recuperação eficientes de dados estruturados em grande escala.
**Flexibilidade de Esquema**: Suportar abordagens de esquema-na-escrita e esquema-na-leitura para acomodar diversas fontes de dados.
**Compatibilidade com Versões Anteriores**: Preservar a funcionalidade existente do TrustGraph, adicionando recursos de dados estruturados.

## Contexto

Atualmente, o TrustGraph se destaca no processamento de dados não estruturados e na construção de grafos de conhecimento a partir de diversas fontes. No entanto, muitos casos de uso empresariais envolvem dados que são inerentemente estruturados - registros de clientes, logs de transações, bancos de dados de inventário e outros conjuntos de dados tabulares. Esses conjuntos de dados estruturados geralmente precisam ser analisados ​​juntamente com conteúdo não estruturado para fornecer insights abrangentes.

As limitações atuais incluem:
Ausência de suporte nativo para ingestão de formatos de dados pré-estruturados (CSV, arrays JSON, exportações de banco de dados).
Impossibilidade de preservar a estrutura inerente ao extrair dados tabulares de documentos.
Falta de mecanismos de consulta eficientes para padrões de dados estruturados.
Falta de uma ponte entre consultas semelhantes a SQL e as consultas de grafo do TrustGraph.

Esta especificação aborda essas lacunas, introduzindo uma camada de dados estruturados que complementa as capacidades existentes do TrustGraph. Ao suportar dados estruturados nativamente, o TrustGraph pode:
Servir como uma plataforma unificada para análise de dados estruturados e não estruturados.
Permitir consultas híbridas que abrangem relacionamentos de grafo e dados tabulares.
Fornecer interfaces familiares para usuários acostumados a trabalhar com dados estruturados.
Desbloquear novos casos de uso em integração de dados e inteligência de negócios.

## Design Técnico

### Arquitetura

A integração de dados estruturados requer os seguintes componentes técnicos:

1. **Serviço de Conversão de Linguagem Natural para Consulta Estruturada**
   Converte perguntas em linguagem natural em consultas estruturadas.
   Suporta vários alvos de linguagem de consulta (inicialmente sintaxe semelhante a SQL).
   Integra-se com as capacidades existentes de NLP do TrustGraph.
   
   Módulo: trustgraph-flow/trustgraph/query/nlp_query/cassandra

2. **Suporte para Esquema de Configuração** ✅ **[COMPLETO]**
   Sistema de configuração estendido para armazenar esquemas de dados estruturados.
   Suporte para definir estruturas de tabela, tipos de campo e relacionamentos.
   Versionamento de esquema e capacidades de migração.

3. **Módulo de Extração de Objetos** ✅ **[COMPLETO]**
   Integração aprimorada do fluxo de extração de conhecimento.
   Identifica e extrai objetos estruturados de fontes não estruturadas.
   Mantém a rastreabilidade e as pontuações de confiança.
   Registra um manipulador de configuração (exemplo: trustgraph-flow/trustgraph/prompt/template/service.py) para receber dados de configuração e decodificar informações de esquema.
   Recebe objetos e os decodifica em objetos ExtractedObject para entrega na fila Pulsar.
   OBS: Existe código existente em `trustgraph-flow/trustgraph/extract/object/row/`. Esta foi uma tentativa anterior e precisará ser refatorada significativamente, pois não está em conformidade com as APIs atuais. Use-o se for útil, comece do zero se não for.
   Requer uma interface de linha de comando: `kg-extract-objects`

   Módulo: trustgraph-flow/trustgraph/extract/kg/objects/

4. **Módulo de Escrita de Armazenamento Estruturado** ✅ **[COMPLETO]**
   Recebe objetos no formato ExtractedObject de filas Pulsar.
   Implementação inicial direcionada ao Apache Cassandra como o armazenamento de dados estruturados.
   Lida com a criação dinâmica de tabelas com base nos esquemas encontrados.
   Gerencia o mapeamento de esquema para tabela Cassandra e a transformação de dados.
   Fornece operações de gravação em lote e em streaming para otimização de desempenho.
   Sem saídas Pulsar - este é um serviço terminal no fluxo de dados.

   **Manipulação de Esquema**:
   Monitora mensagens ExtractedObject recebidas para referências de esquema.
   Quando um novo esquema é encontrado pela primeira vez, cria automaticamente a tabela Cassandra correspondente.
   Mantém um cache de esquemas conhecidos para evitar tentativas redundantes de criação de tabela.
   Deve considerar se deve receber definições de esquema diretamente ou confiar em nomes de esquema em mensagens ExtractedObject.

   **Mapeamento de Tabela Cassandra**:
   O keyspace é nomeado a partir do campo `user` do Metadata do ExtractedObject.
   A tabela é nomeada a partir do campo `schema_name` do ExtractedObject.
   A coleção do Metadata se torna parte da chave de partição para garantir:
     Distribuição natural dos dados em todos os nós do Cassandra.
     Consultas eficientes dentro de uma coleção específica.
     Isolamento lógico entre diferentes importações/fontes de dados.
   Estrutura da chave primária: `PRIMARY KEY ((collection, <schema_primary_key_fields>), <clustering_keys>)`.
     A coleção é sempre o primeiro componente da chave de partição.
     Os campos da chave primária definidos no esquema seguem como parte da chave de partição composta.
     Isso requer que as consultas especifiquem a coleção, garantindo um desempenho previsível.
   As definições de campos são mapeadas para colunas do Cassandra com conversões de tipo:
     `string` → `text`.
     `integer` → `int` ou `bigint` com base na dica de tamanho.
     `float` → `float` ou `double` com base nas necessidades de precisão.
     `boolean` → `boolean`.
     `timestamp` → `timestamp`.
     `enum` → `text` com validação no nível da aplicação.
   Campos indexados criam índices secundários do Cassandra (excluindo campos já na chave primária).
   Campos obrigatórios são aplicados no nível da aplicação (o Cassandra não suporta NOT NULL).

   **Armazenamento de Objetos**:
   Extrai valores do mapa ExtractedObject.values.
   Realiza conversão de tipo e validação antes da inserção.
   Lida com campos opcionais ausentes de forma elegante.
   Mantém metadados sobre a origem do objeto (documento de origem, pontuações de confiança).
   Suporta escritas idempotentes para lidar com cenários de repetição de mensagens.

   **Observações de Implementação**:
   O código existente em `trustgraph-flow/trustgraph/storage/objects/cassandra/` está desatualizado e não está em conformidade com as APIs atuais.
   Deve referenciar `trustgraph-flow/trustgraph/storage/triples/cassandra` como um exemplo de um processador de armazenamento funcional.
   É necessário avaliar o código existente para identificar quaisquer componentes reutilizáveis antes de decidir refatorar ou reescrever.

   Módulo: trustgraph-flow/trustgraph/storage/objects/cassandra

5. **Serviço de Consulta Estruturada** ✅ **[COMPLETO]**
   Aceita consultas estruturadas em formatos definidos.
   Executa consultas no armazenamento estruturado.
   Retorna objetos que correspondem aos critérios da consulta.
   Suporta paginação e filtragem de resultados.

   Módulo: trustgraph-flow/trustgraph/query/objects/cassandra

6. **Integração com Ferramenta de Agente**
   Nova classe de ferramenta para frameworks de agente.
   Permite que agentes consultem armazenamentos de dados estruturados.
   Fornece interfaces de consulta em linguagem natural e estruturada.
   Integra-se com os processos de tomada de decisão existentes dos agentes.

7. **Serviço de Ingestão de Dados Estruturados**
   Aceita dados estruturados em vários formatos (JSON, CSV, XML).
   Analisa e valida os dados recebidos de acordo com os esquemas definidos.
   Converte os dados em fluxos de objetos normalizados.
   Emite objetos para as filas de mensagens apropriadas para processamento.
   Suporta uploads em lote e ingestão em streaming.

   Módulo: trustgraph-flow/trustgraph/decoding/structured

8. **Serviço de Incorporação de Objetos**
   Gera incorporações vetoriais para objetos estruturados.
   Permite a pesquisa semântica em dados estruturados.
   Suporta pesquisa híbrida combinando consultas estruturadas com similaridade semântica.
   Integra-se com armazenamentos de vetores existentes.

   Módulo: trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant

### Modelos de Dados

#### Mecanismo de Armazenamento de Esquemas

Os esquemas são armazenados no sistema de configuração do TrustGraph usando a seguinte estrutura:

**Type**: `schema` (valor fixo para todos os esquemas de dados estruturados)
**Key**: O nome/identificador exclusivo do esquema (por exemplo, `customer_records`, `transaction_log`)
**Value**: Definição de esquema JSON contendo a estrutura

Exemplo de entrada de configuração:
```
Type: schema
Key: customer_records
Value: {
  "name": "customer_records",
  "description": "Customer information table",
  "fields": [
    {
      "name": "customer_id",
      "type": "string",
      "primary_key": true
    },
    {
      "name": "name",
      "type": "string",
      "required": true
    },
    {
      "name": "email",
      "type": "string",
      "required": true
    },
    {
      "name": "registration_date",
      "type": "timestamp"
    },
    {
      "name": "status",
      "type": "string",
      "enum": ["active", "inactive", "suspended"]
    }
  ],
  "indexes": ["email", "registration_date"]
}
```

Esta abordagem permite:
Definição dinâmica de esquema sem alterações de código
Atualizações e versionamento de esquema fáceis
Integração consistente com o gerenciamento de configuração existente do TrustGraph
Suporte para vários esquemas dentro de um único ambiente de implantação

### APIs

Novas APIs:
  Esquemas Pulsar para os tipos acima
  Interfaces Pulsar em novos fluxos
  É necessário um meio de especificar os tipos de esquema nos fluxos para que os fluxos saibam quais
    tipos de esquema carregar
  APIs adicionadas ao gateway e rev-gateway

APIs modificadas:
Pontos de extremidade de extração de conhecimento - Adicionar opção de saída de objeto estruturado
Pontos de extremidade do agente - Adicionar suporte para ferramentas de dados estruturados

### Detalhes da Implementação

Seguindo as convenções existentes - estes são apenas novos módulos de processamento.
Tudo está nos pacotes trustgraph-flow, exceto os itens de esquema
em trustgraph-base.

É necessário algum trabalho de interface do usuário no Workbench para poder demonstrar / testar
essa funcionalidade.

## Considerações de Segurança

Nenhuma consideração adicional.

## Considerações de Desempenho

Algumas perguntas sobre o uso de consultas e índices do Cassandra para que as consultas
não diminuam a velocidade.

## Estratégia de Teste

Use a estratégia de teste existente, serão criados testes unitários, de contrato e de integração.

## Plano de Migração

Nenhum.

## Cronograma

Não especificado.

## Perguntas Abertas

Isso pode ser adaptado para funcionar com outros tipos de armazenamento? Estamos buscando usar
  interfaces que tornem os módulos que funcionam com um armazenamento aplicáveis a
  outros armazenamentos.

## Referências

n/a.

