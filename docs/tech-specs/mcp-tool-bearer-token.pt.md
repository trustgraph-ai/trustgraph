# Especificação de Autenticação de Token Bearer para Ferramentas MCP

> **⚠️ IMPORTANTE: APENAS PARA AMBIENTES DE ÚNICO LOCATÁRIO**
>
> Esta especificação descreve um mecanismo de autenticação básico, de nível de serviço, para ferramentas MCP. Não é uma solução de autenticação completa e não é adequada para:
> - Ambientes multiusuário
> - Implantações multi-tenant
> - Autenticação federada
> - Propagação do contexto do usuário
> - Autorização por usuário
>
> Este recurso fornece **um token estático por ferramenta MCP**, compartilhado entre todos os usuários e sessões. Se você precisar de autenticação por usuário ou por tenant, esta não é a solução certa.

## Visão Geral
**Nome do Recurso**: Suporte para Autenticação de Token Bearer para Ferramentas MCP
**Autor**: Claude Code Assistant
**Data**: 2025-11-11
**Status**: Em Desenvolvimento

### Resumo Executivo

Permite que as configurações de ferramentas MCP especifiquem tokens bearer opcionais para autenticar com servidores MCP protegidos. Isso permite que o TrustGraph invoque ferramentas MCP hospedadas em servidores que exigem autenticação, sem modificar as interfaces de invocação de agentes ou ferramentas.

**IMPORTANTE**: Este é um mecanismo de autenticação básico projetado para cenários de autenticação de serviço para serviço, de único tenant. Não é adequado para:
Ambientes multiusuário onde diferentes usuários precisam de credenciais diferentes
Implantações multi-tenant que requerem isolamento por tenant
Cenários de autenticação federada
Autenticação ou autorização em nível de usuário
Gerenciamento de credenciais dinâmico ou atualização de tokens

Este recurso fornece um token bearer estático e de sistema amplo por configuração de ferramenta MCP, compartilhado entre todos os usuários e invocações dessa ferramenta.

### Declaração do Problema

Atualmente, as ferramentas MCP só podem se conectar a servidores MCP acessíveis publicamente. Muitas implantações de produção de MCP exigem autenticação por meio de tokens bearer para segurança. Sem suporte de autenticação:
As ferramentas MCP não podem se conectar a servidores MCP protegidos
Os usuários devem expor servidores MCP publicamente ou implementar proxies reversos
Não há uma maneira padronizada de passar credenciais para conexões MCP
As melhores práticas de segurança não podem ser aplicadas aos endpoints MCP

### Objetivos

[ ] Permitir que as configurações de ferramentas MCP especifiquem um parâmetro opcional `auth-token`
[ ] Atualizar o serviço de ferramenta MCP para usar tokens bearer ao se conectar a servidores MCP
[ ] Atualizar as ferramentas de linha de comando para suportar a configuração/exibição de tokens de autenticação
[ ] Manter a compatibilidade com versões anteriores com configurações MCP sem autenticação
[ ] Documentar as considerações de segurança para o armazenamento de tokens

### Não Objetivos
Atualização dinâmica de tokens ou fluxos OAuth (apenas tokens estáticos)
Criptografia de tokens armazenados (a segurança do sistema de configuração está fora do escopo)
Métodos de autenticação alternativos (autenticação básica, chaves de API, etc.)
Validação ou verificação de expiração de tokens
**Autenticação por usuário**: Este recurso NÃO suporta credenciais específicas do usuário
**Isolamento multi-tenant**: Este recurso NÃO fornece gerenciamento de tokens por tenant
**Autenticação federada**: Este recurso NÃO se integra com provedores de identidade (SSO, OAuth, SAML, etc.)
**Autenticação com contexto**: Os tokens não são passados com base no contexto do usuário ou na sessão

## Contexto e Informações Adicionais

### Estado Atual
As configurações de ferramentas MCP são armazenadas no grupo de configuração `mcp` com esta estrutura:
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

O serviço da ferramenta MCP conecta-se a servidores usando `streamablehttp_client(url)` sem nenhum cabeçalho de autenticação.

### Limitações

**Limitações do Sistema Atual:**
1. **Sem suporte para autenticação**: Não é possível conectar-se a servidores MCP protegidos.
2. **Exposição de segurança**: Os servidores MCP devem ser acessíveis publicamente ou usar apenas segurança em nível de rede.
3. **Problemas de implantação em produção**: Não é possível seguir as melhores práticas de segurança para endpoints de API.

**Limitações desta Solução:**
1. **Apenas para um único tenant**: Um token estático por ferramenta MCP, compartilhado entre todos os usuários.
2. **Sem credenciais por usuário**: Não é possível autenticar-se como diferentes usuários ou passar o contexto do usuário.
3. **Sem suporte para multi-tenant**: Não é possível isolar as credenciais por tenant ou organização.
4. **Apenas tokens estáticos**: Sem suporte para atualização, rotação ou tratamento de expiração de tokens.
5. **Autenticação em nível de serviço**: Autentica o serviço TrustGraph, não usuários individuais.
6. **Contexto de segurança compartilhado**: Todas as invocações de uma ferramenta MCP usam a mesma credencial.

### Aplicabilidade do Caso de Uso

**✅ Casos de Uso Adequados:**
Implantações TrustGraph de um único tenant.
Autenticação de serviço para serviço (TrustGraph → Servidor MCP).
Ambientes de desenvolvimento e teste.
Ferramentas MCP internas acessadas pelo sistema TrustGraph.
Cenários em que todos os usuários compartilham o mesmo nível de acesso à ferramenta MCP.
Credenciais de serviço estáticas e de longa duração.

**❌ Casos de Uso Inadequados:**
Sistemas multiusuário que requerem autenticação por usuário.
Implantações SaaS multi-tenant com requisitos de isolamento de tenant.
Cenários de autenticação federada (SSO, OAuth, SAML).
Sistemas que requerem a propagação do contexto do usuário para os servidores MCP.
Ambientes que precisam de atualização dinâmica de tokens ou tokens de curta duração.
Aplicações em que diferentes usuários precisam de diferentes níveis de permissão.
Requisitos de conformidade para rastreamento de auditoria em nível de usuário.

**Exemplo de Cenário Adequado:**
Uma implantação TrustGraph de uma única organização em que todos os funcionários usam a mesma ferramenta MCP interna (por exemplo, consulta de banco de dados da empresa). O servidor MCP requer autenticação para evitar acesso externo, mas todos os usuários internos têm o mesmo nível de acesso.

**Exemplo de Cenário Inadequado:**
Uma plataforma SaaS TrustGraph multi-tenant em que o Tenant A e o Tenant B precisam acessar seus próprios servidores MCP isolados com credenciais separadas. Este recurso NÃO suporta o gerenciamento de tokens por tenant.

### Componentes Relacionados
**trustgraph-flow/trustgraph/agent/mcp_tool/service.py**: Serviço de invocação da ferramenta MCP.
**trustgraph-cli/trustgraph/cli/set_mcp_tool.py**: Ferramenta de linha de comando para criar/atualizar configurações de MCP.
**trustgraph-cli/trustgraph/cli/show_mcp_tools.py**: Ferramenta de linha de comando para exibir configurações de MCP.
**SDK Python para MCP**: `streamablehttp_client` de `mcp.client.streamable_http`

## Requisitos

### Requisitos Funcionais

1. **Token de Autenticação da Configuração MCP**: As configurações da ferramenta MCP DEVEM suportar um campo opcional `auth-token`.
2. **Uso do Token Bearer**: O serviço da ferramenta MCP DEVE enviar o cabeçalho `Authorization: Bearer {token}` quando um token de autenticação estiver configurado.
3. **Suporte da CLI**: `tg-set-mcp-tool` DEVE aceitar um parâmetro opcional `--auth-token`.
4. **Exibição do Token**: `tg-show-mcp-tools` DEVE indicar quando um token de autenticação está configurado (mascarado por segurança).
5. **Compatibilidade com versões anteriores**: As configurações de ferramentas MCP existentes sem token de autenticação DEVEM continuar a funcionar.

### Requisitos Não Funcionais
1. **Compatibilidade com versões anteriores**: Nenhuma alteração disruptiva para as configurações de ferramentas MCP existentes.
2. **Desempenho**: Nenhum impacto significativo no desempenho da invocação da ferramenta MCP.
3. **Segurança**: Tokens armazenados na configuração (documentar as implicações de segurança).

### Histórias de Usuário

1. Como um **engenheiro de DevOps**, quero configurar tokens bearer para ferramentas MCP para que eu possa proteger os endpoints do servidor MCP.
2. Como um **usuário da CLI**, quero definir tokens de autenticação ao criar ferramentas MCP para que eu possa conectar-me a servidores protegidos.
3. Como um **administrador do sistema**, quero ver quais ferramentas MCP têm a autenticação configurada para que eu possa auditar as configurações de segurança.

## Design

### Arquitetura de Alto Nível
Estender a configuração e o serviço da ferramenta MCP para suportar a autenticação por token bearer:
1. Adicionar um campo opcional `auth-token` ao esquema de configuração da ferramenta MCP.
2. Modificar o serviço da ferramenta MCP para ler o token de autenticação e passá-lo para o cliente HTTP.
3. Atualizar as ferramentas da CLI para suportar a definição e a exibição de tokens de autenticação.
4. Documentar as considerações de segurança e as melhores práticas.

### Esquema de Configuração

**Esquema Atual**:
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

**Novo Esquema** (com token de autenticação opcional):
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api",
  "auth-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Descrições dos Campos**:
`remote-name` (opcional): Nome usado pelo servidor MCP (o padrão é a chave de configuração).
`url` (obrigatório): URL do endpoint do servidor MCP.
`auth-token` (opcional): Token Bearer para autenticação.

### Fluxo de Dados

1. **Armazenamento de Configuração**: O usuário executa `tg-set-mcp-tool --id my-tool --tool-url http://server/api --auth-token xyz123`.
2. **Carregamento da Configuração**: O serviço da ferramenta MCP recebe a atualização da configuração via callback `on_mcp_config()`.
3. **Invocar a Ferramenta**: Quando a ferramenta é invocada:
   O serviço lê `auth-token` da configuração (se presente).
   Cria um dicionário de cabeçalhos: `{"Authorization": "Bearer {token}"}`.
   Passa os cabeçalhos para `streamablehttp_client(url, headers=headers)`.
   O servidor MCP valida o token e processa a solicitação.

### Alterações na API
Nenhuma alteração na API externa - apenas extensão do esquema de configuração.

### Detalhes do Componente

#### Componente 1: service.py (Serviço da Ferramenta MCP)
**Arquivo**: `trustgraph-flow/trustgraph/agent/mcp_tool/service.py`

**Propósito**: Invocar ferramentas MCP em servidores remotos.

**Alterações Necessárias** (no método `invoke_tool()`):
1. Verificar se `auth-token` está presente em `self.mcp_services[name]` config.
2. Criar um dicionário de cabeçalhos com o cabeçalho Authorization, se o token existir.
3. Passar os cabeçalhos para `streamablehttp_client(url, headers=headers)`.

**Código Atual** (linhas 42-89):
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server
        async with streamablehttp_client(url) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method
```

**Código Modificado**:
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        # Build headers with optional bearer token
        headers = {}
        if "auth-token" in self.mcp_services[name]:
            token = self.mcp_services[name]["auth-token"]
            headers["Authorization"] = f"Bearer {token}"

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server with headers
        async with streamablehttp_client(url, headers=headers) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method (unchanged)
```

#### Componente 2: set_mcp_tool.py (Ferramenta de Configuração de Linha de Comando)
**Arquivo**: `trustgraph-cli/trustgraph/cli/set_mcp_tool.py`

**Propósito**: Criar/atualizar configurações da ferramenta MCP

**Alterações Necessárias**:
1. Adicionar argumento opcional `--auth-token` a argparse
2. Incluir `auth-token` na configuração JSON quando fornecido

**Argumentos Atuais**:
`--id` (obrigatório): Identificador da ferramenta MCP
`--remote-name` (opcional): Nome da ferramenta MCP remota
`--tool-url` (obrigatório): Endpoint da URL da ferramenta MCP
`-u, --api-url` (opcional): URL da API TrustGraph

**Novo Argumento**:
`--auth-token` (opcional): Token Bearer para autenticação

**Construção de Configuração Modificada**:
```python
# Build configuration object
config = {
    "url": args.tool_url,
}

if args.remote_name:
    config["remote-name"] = args.remote_name

if args.auth_token:
    config["auth-token"] = args.auth_token

# Store configuration
api.config().put([
    ConfigValue(type="mcp", key=args.id, value=json.dumps(config))
])
```

#### Componente 3: show_mcp_tools.py (Ferramenta de Exibição de Linha de Comando)
**Arquivo**: `trustgraph-cli/trustgraph/cli/show_mcp_tools.py`

**Propósito**: Exibir configurações da ferramenta MCP

**Alterações Necessárias**:
1. Adicionar coluna "Auth" à tabela de saída
2. Exibir "Sim" ou "Não" com base na presença de auth-token
3. Não exibir o valor real do token (segurança)

**Saída Atual**:
```
ID          Remote Name    URL
----------  -------------  ------------------------
my-tool     my-tool        http://server:3000/api
```

**Nova Saída**:
```
ID          Remote Name    URL                      Auth
----------  -------------  ------------------------ ------
my-tool     my-tool        http://server:3000/api   Yes
other-tool  other-tool     http://other:3000/api    No
```

#### Componente 4: Documentação
**Arquivo**: `docs/cli/tg-set-mcp-tool.md`

**Alterações Necessárias**:
1. Documentar o novo parâmetro `--auth-token`
2. Fornecer um exemplo de uso com autenticação
3. Documentar as considerações de segurança

## Plano de Implementação

### Fase 1: Criar Especificação Técnica
[x] Escrever uma especificação técnica abrangente documentando todas as alterações

### Fase 2: Atualizar o Serviço MCP Tool
[ ] Modificar `invoke_tool()` em `service.py` para ler o token de autenticação da configuração
[ ] Criar um dicionário de cabeçalhos e passá-lo para `streamablehttp_client`
[ ] Testar com um servidor MCP autenticado

### Fase 3: Atualizar as Ferramentas CLI
[ ] Adicionar o argumento `--auth-token` a `set_mcp_tool.py`
[ ] Incluir o token de autenticação no arquivo de configuração JSON
[ ] Adicionar a coluna "Auth" à saída de `show_mcp_tools.py`
[ ] Testar as alterações nas ferramentas CLI

### Fase 4: Atualizar a Documentação
[ ] Documentar o parâmetro `--auth-token` em `tg-set-mcp-tool.md`
[ ] Adicionar uma seção de considerações de segurança
[ ] Fornecer um exemplo de uso

### Fase 5: Testes
[ ] Testar se a ferramenta MCP se conecta com sucesso usando o token de autenticação
[ ] Testar a compatibilidade com versões anteriores (ferramentas sem token de autenticação ainda funcionam)
[ ] Testar se as ferramentas CLI aceitam e armazenam corretamente o token de autenticação
[ ] Testar se o comando "show" exibe o status de autenticação corretamente

### Resumo das Alterações no Código
| Arquivo | Tipo de Alteração | Linhas | Descrição |
|------|------------|-------|-------------|
| `service.py` | Modificado | ~52-66 | Adicionar leitura do token de autenticação e construção de cabeçalhos |
| `set_mcp_tool.py` | Modificado | ~30-60 | Adicionar argumento --auth-token e armazenamento na configuração |
| `show_mcp_tools.py` | Modificado | ~40-70 | Adicionar coluna Auth à exibição |
| `tg-set-mcp-tool.md` | Modificado | Várias | Documentar novo parâmetro |

## Estratégia de Testes

### Testes Unitários
**Leitura do Token de Autenticação**: Testar se `invoke_tool()` lê corretamente o token de autenticação da configuração
**Construção de Cabeçalhos**: Testar se o cabeçalho de Autorização é construído corretamente com o prefixo Bearer
**Compatibilidade com Versões Anteriores**: Testar se as ferramentas sem token de autenticação funcionam inalteradas
**Análise de Argumentos da CLI**: Testar se o argumento `--auth-token` é analisado corretamente

### Testes de Integração
**Conexão Autenticada**: Testar se o serviço da ferramenta MCP se conecta a um servidor autenticado
**Teste de Ponta a Ponta**: Testar o fluxo da CLI → armazenamento na configuração → invocação do serviço com o token de autenticação
**Token Não Necessário**: Testar a conexão com um servidor não autenticado ainda funciona

### Testes Manuais
**Servidor MCP Real**: Testar com um servidor MCP real que requer autenticação com token Bearer
**Fluxo de Trabalho da CLI**: Testar o fluxo de trabalho completo: configurar a ferramenta com autenticação → invocar a ferramenta → verificar o sucesso
**Mascaramento de Autenticação**: Verificar se o status de autenticação é exibido, mas o valor do token não é exposto

## Migração e Implantação

### Estratégia de Migração
Não é necessária migração - esta é uma funcionalidade puramente adicional:
As configurações existentes da ferramenta MCP sem `auth-token` continuam a funcionar inalteradas
Novas configurações podem incluir opcionalmente o campo `auth-token`
As ferramentas CLI aceitam, mas não exigem o parâmetro `--auth-token`

### Plano de Implantação
1. **Fase 1**: Implantar as alterações principais do serviço no desenvolvimento/ambiente de teste
2. **Fase 2**: Implantar as atualizações das ferramentas CLI
3. **Fase 3**: Atualizar a documentação
4. **Fase 4**: Implantação em produção com monitoramento

### Plano de Reversão
As alterações principais são compatíveis com versões anteriores - as ferramentas existentes não são afetadas
Se surgirem problemas, o tratamento do token de autenticação pode ser desativado removendo a lógica de construção de cabeçalhos
As alterações da CLI são independentes e podem ser revertidas separadamente

## Considerações de Segurança

### ⚠️ Limitação Crítica: Apenas Autenticação para um Único Inquilino

**Este mecanismo de autenticação NÃO é adequado para ambientes multiusuário ou multi-inquilino.**

**Credenciais compartilhadas**: Todos os usuários e invocações compartilham o mesmo token por ferramenta MCP
**Sem contexto de usuário**: O servidor MCP não pode distinguir entre diferentes usuários do TrustGraph
**Sem isolamento de inquilino**: Todos os inquilinos compartilham a mesma credencial para cada ferramenta MCP
**Limitação do registro de auditoria**: O servidor MCP registra todas as solicitações da mesma credencial
**Escopo de permissão**: Não é possível impor diferentes níveis de permissão para diferentes usuários

**NÃO use este recurso se:**
Seu deployment do TrustGraph atende a várias organizações (multi-inquilino)
Você precisa rastrear qual usuário acessou qual ferramenta MCP
Diferentes usuários precisam de diferentes níveis de permissão
Você precisa cumprir requisitos de auditoria em nível de usuário
Seu servidor MCP impõe limites de taxa ou cotas por usuário

**Soluções alternativas para cenários multiusuário/multilocatário:**
Implementar a propagação do contexto do usuário por meio de cabeçalhos personalizados
Implantar instâncias separadas do TrustGraph por locatário
Usar isolamento em nível de rede (VPCs, malhas de serviço)
Implementar uma camada de proxy que lida com a autenticação por usuário

### Armazenamento de Tokens
**Risco**: Tokens de autenticação armazenados em texto simples no sistema de configuração

**Mitigação**:
Documentar que os tokens são armazenados sem criptografia
Recomendar o uso de tokens de curta duração sempre que possível
Recomendar controles de acesso adequados no armazenamento de configuração
Considerar uma melhoria futura para o armazenamento de tokens criptografados

### Exposição de Tokens
**Risco**: Tokens podem ser expostos em logs ou na saída da linha de comando

**Mitigação**:
Não registrar os valores dos tokens (registrar apenas "autenticação configurada: sim/não")
O comando de exibição da linha de comando mostra apenas o status mascarado, não o token real
Não incluir tokens em mensagens de erro

### Segurança da Rede
**Risco**: Tokens transmitidos por conexões não criptografadas

**Mitigação**:
Documentar a recomendação de usar URLs HTTPS para servidores MCP
Alertar os usuários sobre o risco de transmissão em texto simples com HTTP

### Acesso à Configuração
**Risco**: Acesso não autorizado ao sistema de configuração expõe tokens

**Mitigação**:
Documentar a importância de proteger o acesso ao sistema de configuração
Recomendar o princípio do menor privilégio para o acesso à configuração
Considerar o registro de auditoria para alterações na configuração (melhoria futura)

### Ambientes Multiusuário
**Risco**: Em implantações multiusuário, todos os usuários compartilham as mesmas credenciais do MCP

**Entendendo o Risco**:
O usuário A e o usuário B usam o mesmo token ao acessar uma ferramenta MCP
O servidor MCP não consegue distinguir entre diferentes usuários do TrustGraph
Não há como impor permissões ou limites de taxa por usuário
Os logs de auditoria no servidor MCP mostram todos os pedidos da mesma credencial
Se a sessão de um usuário for comprometida, o invasor terá o mesmo acesso ao MCP que todos os usuários

**Isso NÃO é um bug - é uma limitação fundamental deste design.**

## Impacto no Desempenho
**Sobrecarga mínima**: A construção do cabeçalho adiciona um tempo de processamento insignificante
**Impacto na rede**: O cabeçalho HTTP adicional adiciona ~50-200 bytes por solicitação
**Uso de memória**: Aumento insignificante para armazenar a string do token na configuração

## Documentação

### Documentação do Usuário
[ ] Atualizar `tg-set-mcp-tool.md` com o parâmetro `--auth-token`
[ ] Adicionar seção de considerações de segurança
[ ] Fornecer exemplo de uso com token de portador
[ ] Documentar as implicações do armazenamento de tokens

### Documentação para Desenvolvedores
[ ] Adicionar comentários inline para o tratamento de tokens de autenticação em `service.py`
[ ] Documentar a lógica de construção de cabeçalhos
[ ] Atualizar a documentação do esquema de configuração da ferramenta MCP

## Perguntas Abertas
1. **Criptografia de tokens**: Devemos implementar o armazenamento de tokens criptografados no sistema de configuração?
2. **Atualização de tokens**: Suporte futuro para fluxos de atualização OAuth ou rotação de tokens?
3. **Métodos de autenticação alternativos**: Devemos suportar autenticação básica, chaves de API ou outros métodos?

## Alternativas Consideradas

1. **Variáveis de ambiente para tokens**: Armazenar tokens em variáveis de ambiente em vez de configuração
   **Rejeitado**: Complica o gerenciamento de implantação e configuração

2. **Armazenamento de segredos separado**: Usar um sistema dedicado de gerenciamento de segredos
   **Adiado**: Fora do escopo da implementação inicial, considerar uma melhoria futura

3. **Múltiplos métodos de autenticação**: Suportar Basic, API key, OAuth, etc.
   **Rejeitado**: Tokens de portador cobrem a maioria dos casos de uso, manter a implementação inicial simples

4. **Armazenamento de tokens criptografado**: Criptografar tokens no sistema de configuração
   **Adiado**: A segurança do sistema de configuração é uma preocupação mais ampla, adiar para trabalhos futuros

5. **Tokens por invocação**: Permitir que os tokens sejam passados no momento da invocação
   **Rejeitado**: Viola a separação de responsabilidades, o agente não deve lidar com credenciais

## Referências
[Especificação do Protocolo MCP](https://github.com/modelcontextprotocol/spec)
[Autenticação Bearer HTTP (RFC 6750)](https://tools.ietf.org/html/rfc6750)
[Serviço da Ferramenta MCP Atual](../trustgraph-flow/trustgraph/agent/mcp_tool/service.py)
[Especificação de Argumentos da Ferramenta MCP](./mcp-tool-arguments.md)

## Apêndice

### Exemplo de Uso

**Configuração da ferramenta MCP com autenticação**:
```bash
tg-set-mcp-tool \
  --id secure-tool \
  --tool-url https://secure-server.example.com/mcp \
  --auth-token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Exibindo ferramentas MCP:**
```bash
tg-show-mcp-tools

ID            Remote Name   URL                                    Auth
-----------   -----------   ------------------------------------   ------
secure-tool   secure-tool   https://secure-server.example.com/mcp  Yes
public-tool   public-tool   http://localhost:3000/mcp              No
```

### Exemplo de Configuração

**Armazenado no sistema de configuração**:
```json
{
  "type": "mcp",
  "key": "secure-tool",
  "value": "{\"url\": \"https://secure-server.example.com/mcp\", \"auth-token\": \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\"}"
}
```

### Melhores Práticas de Segurança

1. **Use HTTPS**: Utilize sempre URLs HTTPS para servidores MCP com autenticação.
2. **Tokens de curta duração**: Utilize tokens com data de expiração sempre que possível.
3. **Privilégios mínimos**: Conceda aos tokens as permissões mínimas necessárias.
4. **Controle de acesso**: Restrinja o acesso ao sistema de configuração.
5. **Rotação de tokens**: Rotacione os tokens regularmente.
6. **Registro de auditoria**: Monitore as alterações de configuração para eventos de segurança.
