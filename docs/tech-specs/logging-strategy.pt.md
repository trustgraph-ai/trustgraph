# Estratégia de Registro (Logging) do TrustGraph

## Visão Geral

O TrustGraph utiliza o módulo `logging` integrado do Python para todas as operações de registro, com configuração centralizada e integração opcional com o Loki para agregação de logs. Isso fornece uma abordagem padronizada e flexível para o registro em todos os componentes do sistema.

## Configuração Padrão

### Nível de Registro
**Nível Padrão**: `INFO`
**Configurável via**: argumento de linha de comando `--log-level`
**Opções**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### Destinos de Saída
1. **Console (stdout)**: Sempre habilitado - garante compatibilidade com ambientes conteinerizados.
2. **Loki**: Agregação de logs centralizada opcional (habilitada por padrão, pode ser desabilitada).

## Módulo de Registro Centralizado

Toda a configuração de registro é gerenciada pelo módulo `trustgraph.base.logging`, que fornece:
`add_logging_args(parser)` - Adiciona argumentos de linha de comando padrão para registro.
`setup_logging(args)` - Configura o registro a partir de argumentos analisados.

Este módulo é usado por todos os componentes do lado do servidor:
Serviços baseados em AsyncProcessor.
API Gateway.
Servidor MCP.

## Diretrizes de Implementação

### 1. Inicialização do Logger

Cada módulo deve criar seu próprio logger usando o módulo `__name__`:

```python
import logging

logger = logging.getLogger(__name__)
```

O nome do logger é automaticamente usado como um rótulo no Loki para filtragem e pesquisa.

### 2. Inicialização do Serviço

Todos os serviços do lado do servidor recebem automaticamente a configuração de registro através do módulo centralizado:

```python
from trustgraph.base import add_logging_args, setup_logging
import argparse

def main():
    parser = argparse.ArgumentParser()

    # Add standard logging arguments (includes Loki configuration)
    add_logging_args(parser)

    # Add your service-specific arguments
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()
    args = vars(args)

    # Setup logging early in startup
    setup_logging(args)

    # Rest of your service initialization
    logger = logging.getLogger(__name__)
    logger.info("Service starting...")
```

### 3. Argumentos de Linha de Comando

Todos os serviços suportam estes argumentos de registro:

**Nível de Log:**
```bash
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
```

**Configuração do Loki:**
```bash
--loki-enabled              # Enable Loki (default)
--no-loki-enabled           # Disable Loki
--loki-url URL              # Loki push URL (default: http://loki:3100/loki/api/v1/push)
--loki-username USERNAME    # Optional authentication
--loki-password PASSWORD    # Optional authentication
```

**Exemplos:**
```bash
# Default - INFO level, Loki enabled
./my-service

# Debug mode, console only
./my-service --log-level DEBUG --no-loki-enabled

# Custom Loki server with auth
./my-service --loki-url http://loki.prod:3100/loki/api/v1/push \
             --loki-username admin --loki-password secret
```

### 4. Variáveis de Ambiente

A configuração do Loki suporta a utilização de variáveis de ambiente como valores padrão:

```bash
export LOKI_URL=http://loki.prod:3100/loki/api/v1/push
export LOKI_USERNAME=admin
export LOKI_PASSWORD=secret
```

Os argumentos da linha de comando têm precedência sobre as variáveis de ambiente.

### 5. Melhores Práticas de Registro (Logging)

#### Uso dos Níveis de Log
**DEBUG**: Informações detalhadas para diagnosticar problemas (valores de variáveis, entrada/saída de funções)
**INFO**: Mensagens informativas gerais (serviço iniciado, configuração carregada, marcos de processamento)
**WARNING**: Mensagens de aviso para situações potencialmente perigosas (recursos obsoletos, erros recuperáveis)
**ERROR**: Mensagens de erro para problemas graves (operações com falha, exceções)
**CRITICAL**: Mensagens críticas para falhas do sistema que exigem atenção imediata

#### Formato da Mensagem
```python
# Good - includes context
logger.info(f"Processing document: {doc_id}, size: {doc_size} bytes")
logger.error(f"Failed to connect to database: {error}", exc_info=True)

# Avoid - lacks context
logger.info("Processing document")
logger.error("Connection failed")
```

#### Considerações de Desempenho
```python
# Use lazy formatting for expensive operations
logger.debug("Expensive operation result: %s", expensive_function())

# Check log level for very expensive debug operations
if logger.isEnabledFor(logging.DEBUG):
    debug_data = compute_expensive_debug_info()
    logger.debug(f"Debug data: {debug_data}")
```

### 6. Registro Estruturado com Loki

Para dados complexos, use o registro estruturado com tags adicionais para o Loki:

```python
logger.info("Request processed", extra={
    'tags': {
        'request_id': request_id,
        'user_id': user_id,
        'status': 'success'
    }
})
```

Essas tags se tornam rótulos pesquisáveis no Loki, além de rótulos automáticos:
`severity` - Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
`logger` - Nome do módulo (de `__name__`)

### 7. Registro de Exceções

Sempre inclua rastreamentos de pilha para exceções:

```python
try:
    process_data()
except Exception as e:
    logger.error(f"Failed to process data: {e}", exc_info=True)
    raise
```

### 8. Considerações sobre o Logging Assíncrono

O sistema de logging utiliza manipuladores enfileirados não bloqueantes para o Loki:
A saída para o console é síncrona (rápida)
A saída para o Loki é enfileirada com um buffer de 500 mensagens
Uma thread em segundo plano gerencia a transmissão para o Loki
Não há bloqueio do código principal da aplicação

```python
import asyncio
import logging

async def async_operation():
    logger = logging.getLogger(__name__)
    # Logging is thread-safe and won't block async operations
    logger.info(f"Starting async operation in task: {asyncio.current_task().get_name()}")
```

## Integração com Loki

### Arquitetura

O sistema de registro utiliza os recursos nativos de Python `QueueHandler` e `QueueListener` para a integração não bloqueante com o Loki:

1. **QueueHandler**: Os registros são colocados em uma fila de 500 mensagens (não bloqueante).
2. **Thread em Segundo Plano**: O QueueListener envia os registros para o Loki de forma assíncrona.
3. **Degradação Graciosa**: Se o Loki estiver indisponível, o registro no console continua.

### Rótulos Automáticos

Cada registro enviado para o Loki inclui:
`processor`: Identidade do processador (por exemplo, `config-svc`, `text-completion`, `embeddings`).
`severity`: Nível de registro (DEBUG, INFO, etc.).
`logger`: Nome do módulo (por exemplo, `trustgraph.gateway.service`, `trustgraph.agent.react.service`).

### Rótulos Personalizados

Adicione rótulos personalizados através do parâmetro `extra`:

```python
logger.info("User action", extra={
    'tags': {
        'user_id': user_id,
        'action': 'document_upload',
        'collection': collection_name
    }
})
```

### Consultando Logs no Loki

```logql
# All logs from a specific processor (recommended - matches Prometheus metrics)
{processor="config-svc"}
{processor="text-completion"}
{processor="embeddings"}

# Error logs from a specific processor
{processor="config-svc", severity="ERROR"}

# Error logs from all processors
{severity="ERROR"}

# Logs from a specific processor with text filter
{processor="text-completion"} |= "Processing"

# All logs from API gateway
{processor="api-gateway"}

# Logs from processors matching pattern
{processor=~".*-completion"}

# Logs with custom tags
{processor="api-gateway"} | json | user_id="12345"
```

### Degradação Graciosa

Se o Loki estiver indisponível ou `python-logging-loki` não estiver instalado:
Mensagem de aviso impressa no console
O registro no console continua normalmente
O aplicativo continua em execução
Sem lógica de repetição para a conexão com o Loki (falha rápida, degrade graciosamente)

## Testes

Durante os testes, considere usar uma configuração de registro diferente:

```python
# In test setup
import logging

# Reduce noise during tests
logging.getLogger().setLevel(logging.WARNING)

# Or disable Loki for tests
setup_logging({'log_level': 'WARNING', 'loki_enabled': False})
```

## Integração de Monitoramento

### Formato Padrão
Todos os logs utilizam um formato consistente:
```
2025-01-09 10:30:45,123 - trustgraph.gateway.service - INFO - Request processed
```

Componentes de formatação:
Timestamp (formato ISO com milissegundos)
Nome do logger (caminho do módulo)
Nível de log
Mensagem

### Consultas Loki para Monitoramento

Consultas de monitoramento comuns:

```logql
# Error rate by processor
rate({severity="ERROR"}[5m]) by (processor)

# Top error-producing processors
topk(5, count_over_time({severity="ERROR"}[1h]) by (processor))

# Recent errors with processor name
{severity="ERROR"} | line_format "{{.processor}}: {{.message}}"

# All agent processors
{processor=~".*agent.*"} |= "exception"

# Specific processor error count
count_over_time({processor="config-svc", severity="ERROR"}[1h])
```

## Considerações de Segurança

**Nunca registre informações sensíveis** (senhas, chaves de API, dados pessoais, tokens)
**Sanitize a entrada do usuário** antes de registrar
**Use espaços reservados** para campos sensíveis: `user_id=****1234`
**Autenticação Loki**: Use `--loki-username` e `--loki-password` para implantações seguras
**Transporte seguro**: Use HTTPS para a URL do Loki em produção: `https://loki.prod:3100/loki/api/v1/push`

## Dependências

O módulo de registro centralizado requer:
`python-logging-loki` - Para integração com o Loki (opcional, degradação graciosa se ausente)

Já incluído em `trustgraph-base/pyproject.toml` e `requirements.txt`.

## Caminho de Migração

Para código existente:

1. **Serviços que já usam AsyncProcessor**: Nenhuma alteração necessária, o suporte ao Loki é automático
2. **Serviços que não usam AsyncProcessor** (api-gateway, mcp-server): Já foram atualizados
3. **Ferramentas de linha de comando (CLI)**: Fora do escopo - continue usando print() ou registro simples

### De print() para registro:
```python
# Before
print(f"Processing document {doc_id}")

# After
logger = logging.getLogger(__name__)
logger.info(f"Processing document {doc_id}")
```

## Resumo da Configuração

| Argumento | Padrão | Variável de Ambiente | Descrição |
|----------|---------|---------------------|-------------|
| `--log-level` | `INFO` | - | Nível de log do console e do Loki |
| `--loki-enabled` | `True` | - | Habilitar o registro de log do Loki |
| `--loki-url` | `http://loki:3100/loki/api/v1/push` | `LOKI_URL` | Endpoint de envio do Loki |
| `--loki-username` | `None` | `LOKI_USERNAME` | Nome de usuário de autenticação do Loki |
| `--loki-password` | `None` | `LOKI_PASSWORD` | Senha de autenticação do Loki |
