---
layout: default
title: "Especificação Técnica: Consolidação da Configuração do Cassandra"
parent: "Portuguese (Beta)"
---

# Especificação Técnica: Consolidação da Configuração do Cassandra

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**Status:** Rascunho
**Autor:** Assistente
**Data:** 2024-09-03

## Visão Geral

Esta especificação aborda os padrões de nomenclatura e configuração inconsistentes para os parâmetros de conexão do Cassandra em todo o código-fonte do TrustGraph. Atualmente, existem dois esquemas de nomenclatura de parâmetros diferentes (`cassandra_*` vs `graph_*`), o que leva à confusão e à complexidade da manutenção.

## Declaração do Problema

O código-fonte atualmente usa dois conjuntos distintos de parâmetros de configuração do Cassandra:

1. **Módulos Knowledge/Config/Library** usam:
   `cassandra_host` (lista de hosts)
   `cassandra_user`
   `cassandra_password`

2. **Módulos Graph/Storage** usam:
   `graph_host` (um único host, às vezes convertido em lista)
   `graph_username`
   `graph_password`

3. **Exposição inconsistente na linha de comando**:
   Alguns processadores (por exemplo, `kg-store`) não expõem as configurações do Cassandra como argumentos de linha de comando
   Outros processadores os expõem com nomes e formatos diferentes
   O texto de ajuda não reflete os valores padrão das variáveis de ambiente

Ambos os conjuntos de parâmetros se conectam ao mesmo cluster Cassandra, mas com convenções de nomenclatura diferentes, causando:
Confusão na configuração para os usuários
Aumento da carga de manutenção
Documentação inconsistente
Potencial para configuração incorreta
Impossibilidade de substituir as configurações via linha de comando em alguns processadores

## Solução Proposta

### 1. Padronização dos Nomes dos Parâmetros

Todos os módulos usarão nomes de parâmetros `cassandra_*` consistentes:
`cassandra_host` - Lista de hosts (armazenada internamente como lista)
`cassandra_username` - Nome de usuário para autenticação
`cassandra_password` - Senha para autenticação

### 2. Argumentos da Linha de Comando

Todos os processadores DEVEM expor a configuração do Cassandra por meio de argumentos de linha de comando:
`--cassandra-host` - Lista separada por vírgulas de hosts
`--cassandra-username` - Nome de usuário para autenticação
`--cassandra-password` - Senha para autenticação

### 3. Fallback de Variáveis de Ambiente

Se os parâmetros da linha de comando não forem fornecidos explicitamente, o sistema verificará as variáveis de ambiente:
`CASSANDRA_HOST` - Lista separada por vírgulas de hosts
`CASSANDRA_USERNAME` - Nome de usuário para autenticação
`CASSANDRA_PASSWORD` - Senha para autenticação

### 4. Valores Padrão

Se nem os parâmetros da linha de comando nem as variáveis de ambiente forem especificados:
`cassandra_host` tem como padrão `["cassandra"]`
`cassandra_username` tem como padrão `None` (sem autenticação)
`cassandra_password` tem como padrão `None` (sem autenticação)

### 5. Requisitos do Texto de Ajuda

A saída `--help` deve:
Mostrar os valores das variáveis de ambiente como padrões quando definidos
Nunca exibir valores de senha (exibir `****` ou `<set>` em vez disso)
Indicar claramente a ordem de resolução no texto de ajuda

Exemplo de saída de ajuda:
```
--cassandra-host HOST
    Cassandra host list, comma-separated (default: prod-cluster-1,prod-cluster-2)
    [from CASSANDRA_HOST environment variable]

--cassandra-username USERNAME
    Cassandra username (default: cassandra_user)
    [from CASSANDRA_USERNAME environment variable]
    
--cassandra-password PASSWORD  
    Cassandra password (default: <set from environment>)
```

## Detalhes de Implementação

### Ordem de Resolução de Parâmetros

Para cada parâmetro do Cassandra, a ordem de resolução será:
1. Valor do argumento de linha de comando
2. Variável de ambiente (`CASSANDRA_*`)
3. Valor padrão

### Tratamento de Parâmetros de Host

O parâmetro `cassandra_host`:
A linha de comando aceita uma string separada por vírgulas: `--cassandra-host "host1,host2,host3"`
A variável de ambiente aceita uma string separada por vírgulas: `CASSANDRA_HOST="host1,host2,host3"`
Internamente sempre armazenado como uma lista: `["host1", "host2", "host3"]`
Host único: `"localhost"` → convertido para `["localhost"]`
Já é uma lista: `["host1", "host2"]` → usado como está

### Lógica de Autenticação

A autenticação será usada quando tanto `cassandra_username` quanto `cassandra_password` forem fornecidos:
```python
if cassandra_username and cassandra_password:
    # Use SSL context and PlainTextAuthProvider
else:
    # Connect without authentication
```

## Arquivos a serem modificados

### Módulos que utilizam parâmetros `graph_*` (a serem alterados):
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/rows/cassandra/write.py`
`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`

### Módulos que utilizam parâmetros `cassandra_*` (a serem atualizados com fallback do ambiente):
`trustgraph-flow/trustgraph/tables/config.py`
`trustgraph-flow/trustgraph/tables/knowledge.py`
`trustgraph-flow/trustgraph/tables/library.py`
`trustgraph-flow/trustgraph/storage/knowledge/store.py`
`trustgraph-flow/trustgraph/cores/knowledge.py`
`trustgraph-flow/trustgraph/librarian/librarian.py`
`trustgraph-flow/trustgraph/librarian/service.py`
`trustgraph-flow/trustgraph/config/service/service.py`
`trustgraph-flow/trustgraph/cores/service.py`

### Arquivos de teste a serem atualizados:
`tests/unit/test_cores/test_knowledge_manager.py`
`tests/unit/test_storage/test_triples_cassandra_storage.py`
`tests/unit/test_query/test_triples_cassandra_query.py`
`tests/integration/test_objects_cassandra_integration.py`

## Estratégia de implementação

### Fase 1: Criar um utilitário de configuração comum
Crie funções utilitárias para padronizar a configuração do Cassandra em todos os processadores:

```python
import os
import argparse

def get_cassandra_defaults():
    """Get default values from environment variables or fallback."""
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD')
    }

def add_cassandra_args(parser: argparse.ArgumentParser):
    """
    Add standardized Cassandra arguments to an argument parser.
    Shows environment variable values in help text.
    """
    defaults = get_cassandra_defaults()
    
    # Format help text with env var indication
    host_help = f"Cassandra host list, comma-separated (default: {defaults['host']})"
    if 'CASSANDRA_HOST' in os.environ:
        host_help += " [from CASSANDRA_HOST]"
    
    username_help = f"Cassandra username"
    if defaults['username']:
        username_help += f" (default: {defaults['username']})"
        if 'CASSANDRA_USERNAME' in os.environ:
            username_help += " [from CASSANDRA_USERNAME]"
    
    password_help = "Cassandra password"
    if defaults['password']:
        password_help += " (default: <set>)"
        if 'CASSANDRA_PASSWORD' in os.environ:
            password_help += " [from CASSANDRA_PASSWORD]"
    
    parser.add_argument(
        '--cassandra-host',
        default=defaults['host'],
        help=host_help
    )
    
    parser.add_argument(
        '--cassandra-username',
        default=defaults['username'],
        help=username_help
    )
    
    parser.add_argument(
        '--cassandra-password',
        default=defaults['password'],
        help=password_help
    )

def resolve_cassandra_config(args) -> tuple[list[str], str|None, str|None]:
    """
    Convert argparse args to Cassandra configuration.
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # Convert host string to list
    if isinstance(args.cassandra_host, str):
        hosts = [h.strip() for h in args.cassandra_host.split(',')]
    else:
        hosts = args.cassandra_host
    
    return hosts, args.cassandra_username, args.cassandra_password
```

### Fase 2: Atualizar Módulos Usando Parâmetros `graph_*`
1. Alterar os nomes dos parâmetros de `graph_*` para `cassandra_*`
2. Substituir os métodos personalizados `add_args()` por métodos padronizados `add_cassandra_args()`
3. Usar as funções auxiliares de configuração comuns
4. Atualizar as strings de documentação

Exemplo de transformação:
```python
# OLD CODE
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help=f'Graph host (default: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help=f'Cassandra username'
    )

# NEW CODE  
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Use standard helper
```

### Fase 3: Atualizar Módulos Usando Parâmetros `cassandra_*`
1. Adicionar suporte para argumentos de linha de comando onde estiver faltando (por exemplo, `kg-store`)
2. Substituir as definições de argumentos existentes por `add_cassandra_args()`
3. Usar `resolve_cassandra_config()` para resolução consistente
4. Garantir o tratamento consistente da lista de hosts

### Fase 4: Atualizar Testes e Documentação
1. Atualizar todos os arquivos de teste para usar os novos nomes de parâmetros
2. Atualizar a documentação da CLI
3. Atualizar a documentação da API
4. Adicionar documentação de variáveis de ambiente

## Compatibilidade com Versões Anteriores

Para manter a compatibilidade com versões anteriores durante a transição:

1. **Avisos de descontinuação** para parâmetros `graph_*`
2. **Aliasing de parâmetros** - aceitar tanto os nomes antigos quanto os novos inicialmente
3. **Implementação gradual** ao longo de várias versões
4. **Atualizações na documentação** com um guia de migração

Exemplo de código de compatibilidade com versões anteriores:
```python
def __init__(self, **params):
    # Handle deprecated graph_* parameters
    if 'graph_host' in params:
        warnings.warn("graph_host is deprecated, use cassandra_host", DeprecationWarning)
        params.setdefault('cassandra_host', params.pop('graph_host'))
    
    if 'graph_username' in params:
        warnings.warn("graph_username is deprecated, use cassandra_username", DeprecationWarning)
        params.setdefault('cassandra_username', params.pop('graph_username'))
    
    # ... continue with standard resolution
```

## Estratégia de Testes

1. **Testes unitários** para a lógica de resolução de configuração
2. **Testes de integração** com várias combinações de configuração
3. **Testes de variáveis de ambiente**
4. **Testes de compatibilidade retroativa** com parâmetros obsoletos
5. **Testes do Docker Compose** com variáveis de ambiente

## Atualizações da Documentação

1. Atualizar toda a documentação dos comandos da linha de comando
2. Atualizar a documentação da API
3. Criar um guia de migração
4. Atualizar os exemplos do Docker Compose
5. Atualizar a documentação de referência de configuração

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|------|--------|------------|
| Mudanças que podem afetar os usuários | Alto | Implementar um período de compatibilidade retroativa |
| Confusão na configuração durante a transição | Médio | Documentação clara e avisos de descontinuação |
| Falhas nos testes | Médio | Atualizações abrangentes nos testes |
| Problemas de implantação do Docker | Alto | Atualizar todos os exemplos do Docker Compose |

## Critérios de Sucesso

[ ] Todos os módulos usam nomes de parâmetros `cassandra_*` consistentes
[ ] Todos os processadores expõem as configurações do Cassandra por meio de argumentos da linha de comando
[ ] O texto de ajuda da linha de comando mostra os valores padrão das variáveis de ambiente
[ ] Os valores de senha nunca são exibidos no texto de ajuda
[ ] O fallback de variáveis de ambiente funciona corretamente
[ ] `cassandra_host` é tratado de forma consistente como uma lista internamente
[ ] A compatibilidade retroativa é mantida por pelo menos 2 versões
[ ] Todos os testes passam com o novo sistema de configuração
[ ] A documentação está totalmente atualizada
[ ] Os exemplos do Docker Compose funcionam com variáveis de ambiente

## Cronograma

**Semana 1:** Implementar o utilitário de configuração comum e atualizar os módulos `graph_*`
**Semana 2:** Adicionar suporte a variáveis de ambiente aos módulos `cassandra_*` existentes
**Semana 3:** Atualizar testes e documentação
**Semana 4:** Testes de integração e correção de bugs

## Considerações Futuras

Considerar a extensão desse padrão para outras configurações de banco de dados (por exemplo, Elasticsearch)
Implementar validação de configuração e melhores mensagens de erro
Adicionar suporte para configuração de pool de conexões do Cassandra
Considerar a adição de suporte para arquivos de configuração (.env)
