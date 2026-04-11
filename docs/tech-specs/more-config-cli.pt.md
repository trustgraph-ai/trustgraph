---
layout: default
title: "Mais Configurações - Especificação Técnica da Interface de Linha de Comando (CLI)"
parent: "Portuguese (Beta)"
---

# Mais Configurações - Especificação Técnica da Interface de Linha de Comando (CLI)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visão Geral

Esta especificação descreve as capacidades aprimoradas de configuração por meio da interface de linha de comando para o TrustGraph, permitindo que os usuários gerenciem itens de configuração individuais por meio de comandos de linha de comando granulares. A integração suporta quatro casos de uso primários:

1. **Listar Itens de Configuração**: Exibir chaves de configuração de um tipo específico
2. **Obter Item de Configuração**: Recuperar valores de configuração específicos
3. **Definir Item de Configuração**: Definir ou atualizar itens de configuração individuais
4. **Excluir Item de Configuração**: Remover itens de configuração específicos

## Objetivos

**Controle Granular**: Permitir o gerenciamento de itens de configuração individuais, em vez de operações em lote
**Listagem Baseada em Tipo**: Permitir que os usuários explorem itens de configuração por tipo
**Operações de Item Único**: Fornecer comandos para obter/definir/excluir itens de configuração individuais
**Integração com a API**: Utilizar a API de Configuração existente para todas as operações
**Padrão de CLI Consistente**: Seguir as convenções e padrões de CLI do TrustGraph estabelecidos
**Tratamento de Erros**: Fornecer mensagens de erro claras para operações inválidas
**Saída JSON**: Suportar saída estruturada para uso programático
**Documentação**: Incluir ajuda abrangente e exemplos de uso

## Contexto

Atualmente, o TrustGraph fornece gerenciamento de configuração por meio da API de Configuração e um único comando de linha de comando `tg-show-config` que exibe toda a configuração. Embora isso funcione para visualizar a configuração, ele carece de capacidades de gerenciamento granular.

As limitações atuais incluem:
Não há como listar itens de configuração por tipo a partir da linha de comando
Não há comando de linha de comando para recuperar valores de configuração específicos
Não há comando de linha de comando para definir itens de configuração individuais
Não há comando de linha de comando para excluir itens de configuração específicos

Esta especificação aborda essas lacunas, adicionando quatro novos comandos de linha de comando que fornecem gerenciamento de configuração granular. Ao expor operações individuais da API de Configuração por meio de comandos de linha de comando, o TrustGraph pode:
Permitir o gerenciamento de configuração por script
Permitir a exploração da estrutura de configuração por tipo
Suportar atualizações de configuração direcionadas
Fornecer controle de configuração granular

## Design Técnico

### Arquitetura

A configuração aprimorada da linha de comando requer os seguintes componentes técnicos:

1. **tg-list-config-items**
   Lista chaves de configuração para um tipo especificado
   Chama o método da API Config.list(type)
   Exibe a lista de chaves de configuração
   
   Módulo: `trustgraph.cli.list_config_items`

2. **tg-get-config-item**
   Recupera um(s) item(ns) de configuração específico(s)
   Chama o método da API Config.get(keys)
   Exibe os valores de configuração em formato JSON

   Módulo: `trustgraph.cli.get_config_item`

3. **tg-put-config-item**
   Define ou atualiza um item de configuração
   Chama o método da API Config.put(values)
   Aceita parâmetros de tipo, chave e valor

   Módulo: `trustgraph.cli.put_config_item`

4. **tg-delete-config-item**
   Remove um item de configuração
   Chama o método da API Config.delete(keys)
   Aceita parâmetros de tipo e chave

   Módulo: `trustgraph.cli.delete_config_item`

### Modelos de Dados

#### ConfigKey e ConfigValue

Os comandos utilizam as estruturas de dados existentes de `trustgraph.api.types`:

```python
@dataclasses.dataclass
class ConfigKey:
    type : str
    key : str

@dataclasses.dataclass
class ConfigValue:
    type : str
    key : str
    value : str
```

Esta abordagem permite:
Tratamento de dados consistente entre a interface de linha de comando (CLI) e a API.
Operações de configuração com segurança de tipo.
Formatos de entrada/saída estruturados.
Integração com a API de Configuração existente.

### Especificações de comandos da CLI

#### tg-list-config-items
```bash
tg-list-config-items --type <config-type> [--format text|json] [--api-url <url>]
```
**Propósito**: Listar todas as chaves de configuração para um determinado tipo.
**Chamada da API**: `Config.list(type)`
**Saída**:
  `text` (padrão): Chaves de configuração separadas por quebras de linha.
  `json`: Array JSON de chaves de configuração.

#### tg-get-config-item
```bash
tg-get-config-item --type <type> --key <key> [--format text|json] [--api-url <url>]
```
**Propósito**: Recuperar um item de configuração específico.
**Chamada da API**: `Config.get([ConfigKey(type, key)])`
**Saída**:
  `text` (padrão): Valor de string bruto.
  `json`: Valor de string codificado em JSON.

#### tg-put-config-item
```bash
tg-put-config-item --type <type> --key <key> --value <value> [--api-url <url>]
tg-put-config-item --type <type> --key <key> --stdin [--api-url <url>]
```
**Propósito**: Definir ou atualizar um item de configuração.
**Chamada da API**: `Config.put([ConfigValue(type, key, value)])`
**Opções de Entrada**:
  `--value`: Valor de string fornecido diretamente na linha de comando.
  `--stdin`: Ler o valor da entrada padrão.
**Saída**: Confirmação de sucesso.

#### tg-delete-config-item
```bash
tg-delete-config-item --type <type> --key <key> [--api-url <url>]
```
**Propósito**: Excluir item de configuração
**Chamada da API**: `Config.delete([ConfigKey(type, key)])`
**Saída**: Confirmação de sucesso

### Detalhes da Implementação

Todos os comandos seguem o padrão estabelecido da CLI TrustGraph:
Use `argparse` para análise de argumentos da linha de comando
Importe e use `trustgraph.api.Api` para comunicação com o backend
Siga os mesmos padrões de tratamento de erros dos comandos da CLI existentes
Suporte ao parâmetro padrão `--api-url` para configuração do endpoint da API
Forneça texto de ajuda descritivo e exemplos de uso

#### Tratamento do Formato de Saída

**Formato de Texto (Padrão)**:
`tg-list-config-items`: Uma chave por linha, texto simples
`tg-get-config-item`: Valor de string bruto, sem aspas ou codificação

**Formato JSON**:
`tg-list-config-items`: Array de strings `["key1", "key2", "key3"]`
`tg-get-config-item`: Valor de string codificado em JSON `"actual string value"`

#### Tratamento da Entrada

**tg-put-config-item** suporta dois métodos de entrada mutuamente exclusivos:
`--value <string>`: Valor de string direto na linha de comando
`--stdin`: Leia toda a entrada da entrada padrão como o valor de configuração
O conteúdo da entrada padrão é lido como texto bruto (preservando novas linhas, espaços em branco, etc.)
Suporta o envio por pipe de arquivos, comandos ou entrada interativa

## Considerações de Segurança

**Validação da Entrada**: Todos os parâmetros da linha de comando devem ser validados antes das chamadas da API
**Autenticação da API**: Os comandos herdam os mecanismos de autenticação da API existentes
**Acesso à Configuração**: Os comandos respeitam os controles de acesso à configuração existentes
**Informações de Erro**: As mensagens de erro não devem vazar detalhes confidenciais da configuração

## Considerações de Desempenho

**Operações de Item Único**: Os comandos são projetados para itens individuais, evitando a sobrecarga de operações em lote
**Eficiência da API**: As chamadas diretas da API minimizam as camadas de processamento
**Latência da Rede**: Cada comando faz uma chamada de API, minimizando as viagens de ida e volta na rede
**Uso de Memória**: Pegada de memória mínima para operações de item único

## Estratégia de Teste

**Testes Unitários**: Teste cada módulo de comando da CLI independentemente
**Testes de Integração**: Teste os comandos da CLI contra a API de Configuração em tempo real
**Testes de Tratamento de Erros**: Verifique o tratamento adequado de erros para entradas inválidas
**Compatibilidade da API**: Garanta que os comandos funcionem com as versões existentes da API de Configuração

## Plano de Migração

Nenhuma migração necessária - estes são novos comandos da CLI que complementam a funcionalidade existente:
O comando `tg-show-config` existente permanece inalterado
Novos comandos podem ser adicionados incrementalmente
Nenhuma alteração disruptiva nos fluxos de trabalho de configuração existentes

## Empacotamento e Distribuição

Estes comandos serão adicionados ao pacote `trustgraph-cli` existente:

**Localização do Pacote**: `trustgraph-cli/`
**Arquivos do Módulo**:
`trustgraph-cli/trustgraph/cli/list_config_items.py`
`trustgraph-cli/trustgraph/cli/get_config_item.py`
`trustgraph-cli/trustgraph/cli/put_config_item.py`
`trustgraph-cli/trustgraph/cli/delete_config_item.py`

**Pontos de Entrada**: Adicionados a `trustgraph-cli/pyproject.toml` na seção `[project.scripts]`:
```toml
tg-list-config-items = "trustgraph.cli.list_config_items:main"
tg-get-config-item = "trustgraph.cli.get_config_item:main"
tg-put-config-item = "trustgraph.cli.put_config_item:main"
tg-delete-config-item = "trustgraph.cli.delete_config_item:main"
```

## Tarefas de Implementação

1. **Criar Módulos CLI**: Implementar os quatro módulos de comando CLI em `trustgraph-cli/trustgraph/cli/`
2. **Atualizar pyproject.toml**: Adicionar novos pontos de entrada de comando em `trustgraph-cli/pyproject.toml`
3. **Documentação**: Criar documentação CLI para cada comando em `docs/cli/`
4. **Testes**: Implementar cobertura de testes abrangente
5. **Integração**: Garantir que os comandos funcionem com a infraestrutura TrustGraph existente
6. **Construção do Pacote**: Verificar se os comandos são instalados corretamente com `pip install trustgraph-cli`

## Exemplos de Uso

#### Listar itens de configuração
```bash
# List prompt keys (text format)
tg-list-config-items --type prompt
template-1
template-2
system-prompt

# List prompt keys (JSON format)  
tg-list-config-items --type prompt --format json
["template-1", "template-2", "system-prompt"]
```

#### Obter item de configuração
```bash
# Get prompt value (text format)
tg-get-config-item --type prompt --key template-1
You are a helpful assistant. Please respond to: {query}

# Get prompt value (JSON format)
tg-get-config-item --type prompt --key template-1 --format json
"You are a helpful assistant. Please respond to: {query}"
```

#### Definir item de configuração
```bash
# Set from command line
tg-put-config-item --type prompt --key new-template --value "Custom prompt: {input}"

# Set from file via pipe
cat ./prompt-template.txt | tg-put-config-item --type prompt --key complex-template --stdin

# Set from file via redirect
tg-put-config-item --type prompt --key complex-template --stdin < ./prompt-template.txt

# Set from command output
echo "Generated template: {query}" | tg-put-config-item --type prompt --key auto-template --stdin
```

#### Excluir item de configuração
```bash
tg-delete-config-item --type prompt --key old-template
```

## Perguntas Abertas

Os comandos devem suportar operações em lote (múltiplas chaves) além de itens individuais?
Qual formato de saída deve ser usado para confirmações de sucesso?
Como os tipos de configuração devem ser documentados/descobertos pelos usuários?

## Referências

API de Configuração existente: `trustgraph/api/config.py`
Padrões de CLI: `trustgraph-cli/trustgraph/cli/show_config.py`
Tipos de dados: `trustgraph/api/types.py`
