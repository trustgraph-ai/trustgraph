---
layout: default
title: "Especificação de Argumentos da Ferramenta MCP"
parent: "Portuguese (Beta)"
---

# Especificação de Argumentos da Ferramenta MCP

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visão Geral
**Nome da Funcionalidade**: Suporte a Argumentos da Ferramenta MCP
**Autor**: Claude Code Assistant
**Data**: 2025-08-21
**Status**: Finalizado

### Resumo Executivo

Permitir que agentes ReACT invoquem ferramentas MCP (Protocolo de Contexto do Modelo) com
argumentos definidos de forma adequada, adicionando suporte à especificação de argumentos às
configurações das ferramentas MCP, de forma semelhante a como as ferramentas de modelo de prompt
funcionam atualmente.

### Declaração do Problema

Atualmente, as ferramentas MCP no framework do agente ReACT não podem especificar seus
argumentos esperados. O método `McpToolImpl.get_arguments()` retorna
uma lista vazia, forçando os LLMs a adivinhar a estrutura correta de parâmetros
com base apenas nos nomes e descrições das ferramentas. Isso leva a:
Invocação de ferramentas não confiável devido à suposição de parâmetros
Má experiência do usuário quando as ferramentas falham devido a argumentos incorretos
Ausência de validação dos parâmetros da ferramenta antes da execução
Documentação de parâmetros ausente nos prompts do agente

### Objetivos

[ ] Permitir que as configurações da ferramenta MCP especifiquem os argumentos esperados (nome, tipo, descrição)
[ ] Atualizar o gerenciador de agentes para expor os argumentos da ferramenta MCP aos LLMs por meio de prompts
[ ] Manter a compatibilidade com versões anteriores com as configurações existentes da ferramenta MCP
[ ] Suportar a validação de argumentos semelhante às ferramentas de modelo de prompt

### Não Objetivos
Descoberta dinâmica de argumentos a partir de servidores MCP (melhoria futura)
Validação de tipo de argumento além da estrutura básica
Esquemas de argumentos complexos (objetos aninhados, arrays)

## Contexto e Informações de Base

### Estado Atual
As ferramentas MCP são configuradas no sistema de agente ReACT com metadados mínimos:
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance",
  "description": "Get bank account balance",
  "mcp-tool": "get_bank_balance"
}
```

O método `McpToolImpl.get_arguments()` retorna `[]`, portanto, os LLMs não recebem orientação de argumentos em seus prompts.

### Limitações

1. **Sem especificação de argumentos**: As ferramentas MCP não podem definir parâmetros esperados.
   parâmetros.

2. **Adivinhação de parâmetros do LLM**: Os agentes devem inferir parâmetros a partir dos nomes/descrições das ferramentas.
   
3. **Informações do prompt ausentes**: Os prompts dos agentes não mostram detalhes dos argumentos para as ferramentas MCP.

   4. **Sem validação**: Parâmetros inválidos são detectados apenas no momento da execução da ferramenta MCP.

### Componentes Relacionados
   **trustgraph-flow/agent/react/service.py**: Carregamento de configuração de ferramentas e criação do AgentManager.
**trustgraph-flow/agent/react/tools.py**: Implementação do McpToolImpl.
**trustgraph-flow/agent/react/agent_manager.py**: Geração de prompts com argumentos de ferramentas.
**trustgraph-cli**: Ferramentas de linha de comando para gerenciamento de ferramentas MCP.
**Workbench**: Interface de usuário externa para configuração de ferramentas de agente.

## Requisitos

### Requisitos Funcionais
## Requisitos

### Requisitos Funcionais

1. **Argumentos de Configuração da Ferramenta MCP**: As configurações da ferramenta MCP DEVEM suportar um array opcional `arguments` com campos de nome, tipo e descrição.
2. **Exposição de Argumentos**: `McpToolImpl.get_arguments()` DEVE retornar os argumentos configurados em vez de uma lista vazia.
3. **Integração com Prompts**: Os prompts do agente DEVEM incluir detalhes dos argumentos da ferramenta MCP quando os argumentos forem especificados.
4. **Compatibilidade com Versões Anteriores**: As configurações existentes da ferramenta MCP sem argumentos DEVEM continuar a funcionar.
5. **Suporte para CLI**: A CLI existente `tg-invoke-mcp-tool` suporta argumentos (já implementado).

### Requisitos Não Funcionais
1. **Compatibilidade com Versões Anteriores**: Nenhuma alteração disruptiva para as configurações existentes da ferramenta MCP.
2. **Desempenho**: Nenhum impacto significativo no desempenho da geração de prompts do agente.
3. **Consistência**: O tratamento de argumentos DEVE corresponder aos padrões de ferramentas de modelos de prompt.

### Histórias de Usuário

1. Como um **desenvolvedor de agente**, quero especificar argumentos da ferramenta MCP na configuração para que os LLMs possam invocar ferramentas com parâmetros corretos.
2. Como um **usuário da workbench**, quero configurar argumentos da ferramenta MCP na interface do usuário para que os agentes usem as ferramentas corretamente.
3. Como um **LLM em um agente ReACT**, quero ver as especificações dos argumentos da ferramenta nos prompts para que eu possa fornecer parâmetros corretos.

## Design

### Arquitetura de Alto Nível
Estenda a configuração da ferramenta MCP para corresponder ao padrão do modelo de prompt, adicionando:
1. Um array opcional `arguments` às configurações da ferramenta MCP.
2. Modificações em `McpToolImpl` para aceitar e retornar argumentos configurados.
3. Atualizações no carregamento da configuração para lidar com os argumentos da ferramenta MCP.
4. Garantir que os prompts do agente incluam informações sobre os argumentos da ferramenta MCP.

### Esquema de Configuração
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance", 
  "description": "Get bank account balance",
  "mcp-tool": "get_bank_balance",
  "arguments": [
    {
      "name": "account_id",
      "type": "string", 
      "description": "Bank account identifier"
    },
    {
      "name": "date",
      "type": "string",
      "description": "Date for balance query (optional, format: YYYY-MM-DD)"
    }
  ]
}
```

### Fluxo de Dados
1. **Carregamento de Configuração**: A configuração da ferramenta MCP, juntamente com seus argumentos, é carregada por `on_tools_config()`
2. **Criação da Ferramenta**: Os argumentos são analisados e passados para `McpToolImpl` através do construtor
3. **Geração de Prompt**: `agent_manager.py` chama `tool.arguments` para incluir nos prompts do LLM
4. **Invocar a Ferramenta**: O LLM fornece parâmetros que são passados para o serviço MCP sem modificação

### Alterações na API
Não há alterações na API externa - isso é puramente configuração interna e tratamento de argumentos.

### Detalhes do Componente

#### Componente 1: service.py (Carregamento de Configuração da Ferramenta)
**Propósito**: Analisar as configurações da ferramenta MCP e criar instâncias da ferramenta
**Alterações Necessárias**: Adicionar análise de argumentos para ferramentas MCP (semelhante às ferramentas de prompt)
**Nova Funcionalidade**: Extrair o array `arguments` da configuração da ferramenta MCP e criar objetos `Argument`

#### Componente 2: tools.py (McpToolImpl)
**Propósito**: Wrapper de implementação da ferramenta MCP
**Alterações Necessárias**: Aceitar argumentos no construtor e retorná-los de `get_arguments()`
**Nova Funcionalidade**: Armazenar e expor os argumentos configurados em vez de retornar uma lista vazia

#### Componente 3: Workbench (Repositório Externo)
**Propósito**: Interface do usuário para configurar ferramentas de agente
**Alterações Necessárias**: Adicionar interface do usuário para especificar argumentos para ferramentas MCP
**Nova Funcionalidade**: Permitir que os usuários adicionem/editem/removam argumentos para ferramentas MCP

#### Componente 4: Ferramentas de Linha de Comando
**Propósito**: Gerenciamento de ferramentas de linha de comando
**Alterações Necessárias**: Suportar a especificação de argumentos nos comandos de criação/atualização da ferramenta MCP
**Nova Funcionalidade**: Aceitar o parâmetro de argumentos nos comandos de configuração da ferramenta

## Plano de Implementação

### Fase 1: Alterações no Framework Central do Agente
[ ] Atualizar o construtor de `McpToolImpl` para aceitar o parâmetro `arguments`
[ ] Alterar `McpToolImpl.get_arguments()` para retornar os argumentos armazenados
[ ] Modificar a análise de configuração da ferramenta MCP em `service.py` para lidar com argumentos
[ ] Adicionar testes unitários para o tratamento de argumentos da ferramenta MCP
[ ] Verificar se os prompts do agente incluem os argumentos da ferramenta MCP

### Fase 2: Suporte para Ferramentas Externas
[ ] Atualizar as ferramentas de linha de comando para suportar a especificação de argumentos da ferramenta MCP
[ ] Documentar o formato de configuração de argumentos para os usuários
[ ] Atualizar a interface do usuário do Workbench para suportar a configuração de argumentos da ferramenta MCP
[ ] Adicionar exemplos e documentação

### Resumo das Alterações no Código
| Arquivo | Tipo de Alteração | Descrição |
|------|------------|-------------|
| `tools.py` | Modificado | Atualizar McpToolImpl para aceitar e armazenar argumentos |
| `service.py` | Modificado | Analisar argumentos da configuração da ferramenta MCP (linhas 108-113) |
| `test_react_processor.py` | Modificado | Adicionar testes para argumentos da ferramenta MCP |
| Ferramentas de linha de comando | Modificado | Suportar a especificação de argumentos nos comandos |
| Workbench | Modificado | Adicionar interface do usuário para a configuração de argumentos da ferramenta MCP |

## Estratégia de Teste

### Testes Unitários
**Análise de Argumentos da Ferramenta MCP**: Testar se `service.py` analisa corretamente os argumentos das configurações da ferramenta MCP
**Argumentos do McpToolImpl**: Testar se `get_arguments()` retorna os argumentos configurados em vez de uma lista vazia
**Compatibilidade com Versões Anteriores**: Testar se as ferramentas MCP sem argumentos continuam a funcionar (retornam uma lista vazia)
**Geração de Prompt do Agente**: Testar se os prompts do agente incluem os detalhes dos argumentos da ferramenta MCP

### Testes de Integração
**Invocar Ferramenta de Extremo a Extremo**: O agente de teste com argumentos da ferramenta MCP pode invocar ferramentas com sucesso.
**Carregamento de Configuração**: Testar o ciclo completo de carregamento de configuração com argumentos da ferramenta MCP.
**Componentes Cruzados**: Testar se os argumentos fluem corretamente de config → criação de ferramenta → geração de prompt.

### Testes Manuais
**Comportamento do Agente**: Verificar manualmente se o LLM recebe e usa as informações dos argumentos nos ciclos ReACT.
**Integração com a Linha de Comando**: Testar se tg-invoke-mcp-tool funciona com ferramentas MCP configuradas com novos argumentos.
**Integração com o Workbench**: Testar se a interface do usuário suporta a configuração de argumentos para ferramentas MCP.

## Migração e Implantação

### Estratégia de Migração
Não é necessária migração - esta é uma funcionalidade puramente adicional:
As configurações existentes da ferramenta MCP sem `arguments` continuam a funcionar inalteradas.
`McpToolImpl.get_arguments()` retorna uma lista vazia para ferramentas legadas.
Novas configurações podem incluir opcionalmente o array `arguments`.

### Plano de Implantação
1. **Fase 1**: Implantar as alterações principais do framework do agente para desenvolvimento/staging.
2. **Fase 2**: Implantar as atualizações da ferramenta de linha de comando e a documentação.
3. **Fase 3**: Implantar as atualizações da interface do usuário do Workbench para a configuração de argumentos.
4. **Fase 4**: Implantação em produção com monitoramento.

### Plano de Reversão
As alterações principais são compatíveis com versões anteriores - nenhuma reversão é necessária para a funcionalidade.
Se surgirem problemas, desative a análise de argumentos revertendo a lógica de carregamento da configuração da ferramenta MCP.
As alterações do Workbench e da linha de comando são independentes e podem ser revertidas separadamente.

## Considerações de Segurança
**Nenhuma nova superfície de ataque**: Os argumentos são analisados a partir de fontes de configuração existentes, sem novas entradas.
**Validação de parâmetros**: Os argumentos são passados para as ferramentas MCP sem alterações - a validação permanece no nível da ferramenta MCP.
**Integridade da configuração**: As especificações de argumentos fazem parte da configuração da ferramenta - o mesmo modelo de segurança se aplica.

## Impacto no Desempenho
**Sobrecarga mínima**: A análise de argumentos ocorre apenas durante o carregamento da configuração, não por solicitação.
**Aumento do tamanho do prompt**: Os prompts do agente incluirão detalhes dos argumentos da ferramenta MCP, aumentando ligeiramente o uso de tokens.
**Uso de memória**: Aumento insignificante para armazenar as especificações de argumentos em objetos de ferramenta.

## Documentação

### Documentação do Usuário
[ ] Atualizar o guia de configuração da ferramenta MCP com exemplos de argumentos.
[ ] Adicionar a especificação de argumentos ao texto de ajuda da ferramenta de linha de comando.
[ ] Criar exemplos de padrões comuns de argumentos da ferramenta MCP.

### Documentação para Desenvolvedores
[ ] Atualizar a documentação da classe McpToolImpl.
[ ] Adicionar comentários inline para a lógica de análise de argumentos.
[ ] Documentar o fluxo de argumentos na arquitetura do sistema.

## Perguntas Abertas
1. **Validação de argumentos**: Devemos validar os tipos/formatos de argumentos além da verificação básica da estrutura?
2. **Descoberta dinâmica**: Uma melhoria futura para consultar os servidores MCP para esquemas de ferramentas automaticamente?

## Alternativas Consideradas
1. **Descoberta dinâmica do esquema MCP**: Consultar os servidores MCP para esquemas de argumentos em tempo de execução - rejeitado devido à complexidade e preocupações com a confiabilidade.
2. **Registro de argumentos separado**: Armazenar os argumentos da ferramenta MCP em uma seção de configuração separada - rejeitado devido à inconsistência com a abordagem do modelo de prompt.
3. **Validação de tipo**: Validação completa do esquema JSON para argumentos - adiada como uma melhoria futura para manter a implementação inicial simples.

## Referências
[Especificação do Protocolo MCP](https://github.com/modelcontextprotocol/spec)
[Implementação da Ferramenta do Modelo de Prompt](./trustgraph-flow/trustgraph/agent/react/service.py#L114-129)
[Implementação Atual da Ferramenta MCP](./trustgraph-flow/trustgraph/agent/react/tools.py#L58-86)

## Apêndice
[Quaisquer informações adicionais, diagramas ou exemplos]
