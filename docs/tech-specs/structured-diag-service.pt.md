# Especificação Técnica do Serviço de Diagnóstico de Dados Estruturados

## Visão Geral

Esta especificação descreve um novo serviço invocável para diagnosticar e analisar dados estruturados dentro do TrustGraph. O serviço extrai a funcionalidade da ferramenta de linha de comando existente `tg-load-structured-data` e a expõe como um serviço de solicitação/resposta, permitindo o acesso programático às capacidades de detecção de tipo de dados e geração de descritores.

O serviço suporta três operações principais:

1. **Detecção de Tipo de Dados**: Analisa uma amostra de dados para determinar seu formato (CSV, JSON ou XML)
2. **Geração de Descritor**: Gera um descritor de dados estruturados do TrustGraph para uma determinada amostra de dados e tipo
3. **Diagnóstico Combinado**: Realiza a detecção de tipo e a geração de descritor em sequência

## Objetivos

**Modularização da Análise de Dados**: Extrai a lógica de diagnóstico de dados da CLI para componentes de serviço reutilizáveis
**Habilitar Acesso Programático**: Fornecer acesso baseado em API às capacidades de análise de dados
**Suportar Múltiplos Formatos de Dados**: Lidar com formatos de dados CSV, JSON e XML de forma consistente
**Gerar Descritores Precisos**: Produzir descritores de dados estruturados que mapeiem com precisão os dados de origem para os esquemas do TrustGraph
**Manter a Compatibilidade com Versões Anteriores**: Garantir que a funcionalidade existente da CLI continue a funcionar
**Habilitar a Composição de Serviços**: Permitir que outros serviços aproveitem as capacidades de diagnóstico de dados
**Melhorar a Testabilidade**: Separar a lógica de negócios da interface da CLI para melhor teste
**Suportar a Análise em Streaming**: Permitir a análise de amostras de dados sem carregar arquivos inteiros

## Contexto

Atualmente, o comando `tg-load-structured-data` fornece funcionalidade abrangente para analisar dados estruturados e gerar descritores. No entanto, essa funcionalidade está fortemente acoplada à interface da CLI, limitando sua reutilização.

As limitações atuais incluem:
Lógica de diagnóstico de dados incorporada no código da CLI
Sem acesso programático à detecção de tipo e à geração de descritores
Difícil integrar as capacidades de diagnóstico em outros serviços
Capacidade limitada de compor fluxos de trabalho de análise de dados

Esta especificação aborda essas lacunas, criando um serviço dedicado para o diagnóstico de dados estruturados. Ao expor essas capacidades como um serviço, o TrustGraph pode:
Permitir que outros serviços analisem dados programaticamente
Suportar pipelines de processamento de dados mais complexos
Facilitar a integração com sistemas externos
Melhorar a manutenção por meio da separação de responsabilidades

## Design Técnico

### Arquitetura

O serviço de diagnóstico de dados estruturados requer os seguintes componentes técnicos:

1. **Processador do Serviço de Diagnóstico**
   Lida com solicitações de diagnóstico recebidas
   Orquestra a detecção de tipo e a geração de descritores
   Retorna respostas estruturadas com os resultados do diagnóstico

   Módulo: `trustgraph-flow/trustgraph/diagnosis/structured_data/service.py`

2. **Detector de Tipo de Dados**
   Usa a detecção algorítmica para identificar o formato de dados (CSV, JSON, XML)
   Analisa a estrutura de dados, delimitadores e padrões de sintaxe
   Retorna o formato detectado e as pontuações de confiança

   Módulo: `trustgraph-flow/trustgraph/diagnosis/structured_data/type_detector.py`

3. **Gerador de Descritores**
   Usa o serviço de prompt para gerar descritores
   Invoca prompts específicos do formato (diagnosticar-csv, diagnosticar-json, diagnosticar-xml)
   Mapeia campos de dados para campos de esquema do TrustGraph por meio de respostas de prompt

   Módulo: `trustgraph-flow/trustgraph/diagnosis/structured_data/descriptor_generator.py`

### Modelos de Dados

#### StructuredDataDiagnosisRequest

Mensagem de solicitação para operações de diagnóstico de dados estruturados:

```python
class StructuredDataDiagnosisRequest:
    operation: str  # "detect-type", "generate-descriptor", or "diagnose"
    sample: str     # Data sample to analyze (text content)
    type: Optional[str]  # Data type (csv, json, xml) - required for generate-descriptor
    schema_name: Optional[str]  # Target schema name for descriptor generation
    options: Dict[str, Any]  # Additional options (e.g., delimiter for CSV)
```

#### StructuredDataDiagnosisResponse

Mensagem de resposta contendo os resultados do diagnóstico:

```python
class StructuredDataDiagnosisResponse:
    operation: str  # The operation that was performed
    detected_type: Optional[str]  # Detected data type (for detect-type/diagnose)
    confidence: Optional[float]  # Confidence score for type detection
    descriptor: Optional[Dict]  # Generated descriptor (for generate-descriptor/diagnose)
    error: Optional[str]  # Error message if operation failed
    metadata: Dict[str, Any]  # Additional metadata (e.g., field count, sample records)
```

#### Estrutura do Descritor

O descritor gerado segue o formato existente de descritor de dados estruturados:

```json
{
  "format": {
    "type": "csv",
    "encoding": "utf-8",
    "options": {
      "delimiter": ",",
      "has_header": true
    }
  },
  "mappings": [
    {
      "source_field": "customer_id",
      "target_field": "id",
      "transforms": [
        {"type": "trim"}
      ]
    }
  ],
  "output": {
    "schema_name": "customer",
    "options": {
      "batch_size": 1000,
      "confidence": 0.9
    }
  }
}
```

### Interface de Serviço

O serviço exporá as seguintes operações através do padrão de solicitação/resposta:

1. **Operação de Detecção de Tipo**
   Entrada: Amostra de dados
   Processamento: Analisar a estrutura de dados usando detecção algorítmica
   Saída: Tipo detectado com pontuação de confiança

2. **Operação de Geração de Descritor**
   Entrada: Amostra de dados, tipo, nome do esquema de destino
   Processamento:
     Chamar o serviço de prompt com o ID de prompt específico do formato (diagnosticar-csv, diagnosticar-json ou diagnosticar-xml)
     Passar a amostra de dados e os esquemas disponíveis para o prompt
     Receber o descritor gerado da resposta do prompt
   Saída: Descritor de dados estruturados

3. **Operação de Diagnóstico Combinado**
   Entrada: Amostra de dados, nome de esquema opcional
   Processamento:
     Usar a detecção algorítmica para identificar o formato primeiro
     Selecionar o prompt específico do formato apropriado com base no tipo detectado
     Chamar o serviço de prompt para gerar o descritor
   Saída: Tanto o tipo detectado quanto o descritor

### Detalhes da Implementação

O serviço seguirá as convenções do serviço TrustGraph:

1. **Registro de Serviço**
   Registrar como tipo de serviço `structured-diag`
   Usar tópicos padrão de solicitação/resposta
   Implementar a classe base FlowProcessor
   Registrar PromptClientSpec para a interação com o serviço de prompt

2. **Gerenciamento de Configuração**
   Acessar as configurações do esquema através do serviço de configuração
   Armazenar em cache os esquemas para desempenho
   Lidar com atualizações de configuração dinamicamente

3. **Integração de Prompt**
   Usar a infraestrutura existente do serviço de prompt
   Chamar o serviço de prompt com IDs de prompt específicos do formato:
     `diagnose-csv`: Para análise de dados CSV
     `diagnose-json`: Para análise de dados JSON
     `diagnose-xml`: Para análise de dados XML
   Os prompts são configurados na configuração do prompt, e não codificados no serviço
   Passar esquemas e amostras de dados como variáveis de prompt
   Analisar as respostas do prompt para extrair os descritores

4. **Tratamento de Erros**
   Validar as amostras de dados de entrada
   Fornecer mensagens de erro descritivas
   Lidar com dados malformados de forma elegante
   Lidar com falhas no serviço de prompt

5. **Amostragem de Dados**
   Processar tamanhos de amostra configuráveis
   Lidar com registros incompletos de forma apropriada
   Manter a consistência da amostragem

### Integração de API

O serviço será integrado com as APIs TrustGraph existentes:

Componentes Modificados:
`tg-load-structured-data` CLI - Refatorado para usar o novo serviço para operações de diagnóstico
Flow API - Estendido para suportar solicitações de diagnóstico de dados estruturados

Novos Pontos de Extremidade do Serviço:
`/api/v1/flow/{flow}/diagnose/structured-data` - Endpoint WebSocket para solicitações de diagnóstico
`/api/v1/diagnose/structured-data` - Endpoint REST para diagnóstico síncrono

### Fluxo de Mensagens

```
Client → Gateway → Structured Diag Service → Config Service (for schemas)
                                           ↓
                                    Type Detector (algorithmic)
                                           ↓
                                    Prompt Service (diagnose-csv/json/xml)
                                           ↓
                                 Descriptor Generator (parses prompt response)
                                           ↓
Client ← Gateway ← Structured Diag Service (response)
```

## Considerações de Segurança

Validação de entrada para prevenir ataques de injeção
Limites de tamanho em amostras de dados para prevenir ataques de negação de serviço (DoS)
Sanitização de descritores gerados
Controle de acesso através da autenticação TrustGraph existente

## Considerações de Desempenho

Cache de definições de esquema para reduzir o número de chamadas ao serviço de configuração
Limitar o tamanho das amostras para manter um desempenho responsivo
Usar processamento em fluxo para grandes amostras de dados
Implementar mecanismos de timeout para análises de longa duração

## Estratégia de Testes

1. **Testes Unitários**
   Detecção de tipo para vários formatos de dados
   Precisão da geração de descritores
   Cenários de tratamento de erros

2. **Testes de Integração**
   Fluxo de solicitação/resposta do serviço
   Recuperação e cache de esquema
   Integração com a interface de linha de comando (CLI)

3. **Testes de Desempenho**
   Processamento de grandes amostras
   Tratamento de solicitações concorrentes
   Uso de memória sob carga

## Plano de Migração

1. **Fase 1**: Implementar o serviço com a funcionalidade principal
2. **Fase 2**: Refatorar a CLI para usar o serviço (manter a compatibilidade com versões anteriores)
3. **Fase 3**: Adicionar endpoints de API REST
4. **Fase 4**: Descontinuar a lógica da CLI incorporada (com aviso prévio)

## Cronograma

Semana 1-2: Implementar o serviço principal e a detecção de tipo
Semana 3-4: Adicionar geração de descritores e integração
Semana 5: Testes e documentação
Semana 6: Refatoração da CLI e migração

## Perguntas Abertas

O serviço deve suportar formatos de dados adicionais (por exemplo, Parquet, Avro)?
Qual deve ser o tamanho máximo da amostra para análise?
Os resultados do diagnóstico devem ser armazenados em cache para solicitações repetidas?
Como o serviço deve lidar com cenários de vários esquemas?
Os IDs de prompt devem ser parâmetros configuráveis para o serviço?

## Referências

[Especificação do Descritor de Dados Estruturados](structured-data-descriptor.md)
[Documentação de Carregamento de Dados Estruturados](structured-data.md)
`tg-load-structured-data` implementação: `trustgraph-cli/trustgraph/cli/load_structured_data.py`