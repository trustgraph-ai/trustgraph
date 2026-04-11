# TrustGraph Tool Group System
## Especificação Técnica v1.0

### Resumo Executivo

Esta especificação define um sistema de agrupamento de ferramentas para agentes TrustGraph que permite um controle preciso sobre quais ferramentas estão disponíveis para solicitações específicas. O sistema introduz filtragem de ferramentas baseada em grupos por meio de configuração e especificação no nível da solicitação, permitindo melhores limites de segurança, gerenciamento de recursos e particionamento funcional das capacidades do agente.

### 1. Visão Geral

#### 1.1 Declaração do Problema

Atualmente, os agentes TrustGraph têm acesso a todas as ferramentas configuradas, independentemente do contexto da solicitação ou dos requisitos de segurança. Isso cria vários desafios:

**Risco de Segurança**: Ferramentas sensíveis (por exemplo, modificação de dados) estão disponíveis mesmo para consultas somente leitura.
**Desperdício de Recursos**: Ferramentas complexas são carregadas mesmo quando consultas simples não as exigem.
**Confusão Funcional**: Os agentes podem selecionar ferramentas inadequadas quando alternativas mais simples existem.
**Isolamento Multi-inquilino**: Diferentes grupos de usuários precisam de acesso a conjuntos de ferramentas diferentes.

#### 1.2 Visão Geral da Solução

O sistema de agrupamento de ferramentas introduz:

1. **Classificação por Grupo**: As ferramentas são marcadas com associações de grupo durante a configuração.
2. **Filtragem no Nível da Solicitação**: AgentRequest especifica quais grupos de ferramentas são permitidos.
3. **Aplicação em Tempo de Execução**: Os agentes têm acesso apenas a ferramentas que correspondem aos grupos solicitados.
4. **Agrupamento Flexível**: As ferramentas podem pertencer a vários grupos para cenários complexos.

### 2. Alterações no Esquema

#### 2.1 Aprimoramento do Esquema de Configuração da Ferramenta

A configuração existente da ferramenta é aprimorada com um campo `group`:

**Antes:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query", 
  "description": "Query the knowledge graph"
}
```

**Depois:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"]
}
```

**Especificação do Campo do Grupo:**
`group`: Array(String) - Lista de grupos aos quais esta ferramenta pertence
**Opcional**: Ferramentas sem campo de grupo pertencem ao grupo "padrão"
**Múltipla associação**: As ferramentas podem pertencer a vários grupos
**Sensível a maiúsculas e minúsculas**: Os nomes dos grupos são correspondências exatas de strings

#### 2.1.2 Melhoria da Transição de Estado da Ferramenta

As ferramentas podem, opcionalmente, especificar transições de estado e disponibilidade baseada no estado:

```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"],
  "state": "analysis",
  "available_in_states": ["undefined", "research"]
}
```

**Especificação do Campo de Estado:**
`state`: String - **Opcional** - Estado para o qual transitar após a execução bem-sucedida da ferramenta
`available_in_states`: Array(String) - **Opcional** - Estados nos quais esta ferramenta está disponível
**Comportamento padrão**: Ferramentas sem `available_in_states` estão disponíveis em todos os estados
**Transição de estado**: Ocorre apenas após a execução bem-sucedida da ferramenta

#### 2.2 Melhoria do Esquema AgentRequest

O esquema `AgentRequest` em `trustgraph-base/trustgraph/schema/services/agent.py` é aprimorado:

**AgentRequest Atual:**
`question`: String - Consulta do usuário
`plan`: String - Plano de execução (pode ser removido)
`state`: String - Estado do agente
`history`: Array(AgentStep) - Histórico de execução

**AgentRequest Aprimorado:**
`question`: String - Consulta do usuário
`state`: String - Estado de execução do agente (agora usado ativamente para filtragem de ferramentas)
`history`: Array(AgentStep) - Histórico de execução
`group`: Array(String) - **NOVO** - Grupos de ferramentas permitidos para este pedido

**Alterações no Esquema:**
**Removido**: O campo `plan` não é mais necessário e pode ser removido (originalmente destinado à especificação de ferramentas)
**Adicionado**: O campo `group` para especificação de grupos de ferramentas
**Aprimorado**: O campo `state` agora controla a disponibilidade de ferramentas durante a execução

**Comportamentos dos Campos:**

**Grupo de Campo:**
**Opcional**: Se não especificado, o padrão é ["default"]
**Interseção**: Apenas as ferramentas que correspondem a pelo menos um grupo especificado estão disponíveis
**Array vazio**: Nenhuma ferramenta disponível (o agente só pode usar o raciocínio interno)
**Curinga**: O grupo especial "*" concede acesso a todas as ferramentas

**Campo de Estado:**
**Opcional**: Se não especificado, o padrão é "undefined"
**Filtragem baseada em estado**: Apenas as ferramentas disponíveis no estado atual são elegíveis
**Estado padrão**: O estado "undefined" permite todas as ferramentas (sujeito à filtragem de grupos)
**Transições de estado**: As ferramentas podem alterar o estado após a execução bem-sucedida

### 3. Exemplos de Grupos Personalizados

As organizações podem definir grupos específicos do domínio:

```json
{
  "financial-tools": ["stock-query", "portfolio-analysis"],
  "medical-tools": ["diagnosis-assist", "drug-interaction"],
  "legal-tools": ["contract-analysis", "case-search"]
}
```

### 4. Detalhes de Implementação

#### 4.1 Carregamento e Filtragem de Ferramentas

**Fase de Configuração:**
1. Todas as ferramentas são carregadas da configuração com suas atribuições de grupo.
2. Ferramentas sem grupos explícitos são atribuídas ao grupo "padrão".
3. A associação a grupos é validada e armazenada no registro de ferramentas.

**Fase de Processamento de Solicitações:**
1. Uma solicitação do agente chega com uma especificação de grupo opcional.
2. O agente filtra as ferramentas disponíveis com base na interseção de grupos.
3. Apenas as ferramentas correspondentes são passadas para o contexto de execução do agente.
4. O agente opera com o conjunto de ferramentas filtrado durante todo o ciclo de vida da solicitação.

#### 4.2 Lógica de Filtragem de Ferramentas

**Filtragem Combinada de Grupo e Estado:**

```
For each configured tool:
  tool_groups = tool.group || ["default"]
  tool_states = tool.available_in_states || ["*"]  // Available in all states
  
For each request:
  requested_groups = request.group || ["default"]
  current_state = request.state || "undefined"
  
Tool is available if:
  // Group filtering
  (intersection(tool_groups, requested_groups) is not empty OR "*" in requested_groups)
  AND
  // State filtering  
  (current_state in tool_states OR "*" in tool_states)
```

**Lógica de Transição de Estado:**

```
After successful tool execution:
  if tool.state is defined:
    next_request.state = tool.state
  else:
    next_request.state = current_request.state  // No change
```

#### 4.3 Pontos de Integração do Agente

**Agente ReAct:**
O filtro de ferramentas ocorre em agent_manager.py durante a criação do registro de ferramentas.
A lista de ferramentas disponíveis é filtrada por grupo e estado antes da geração do plano.
As transições de estado atualizam o campo AgentRequest.state após a execução bem-sucedida da ferramenta.
A próxima iteração usa o estado atualizado para o filtro de ferramentas.

**Agente Baseado em Confiança:**
O filtro de ferramentas ocorre em planner.py durante a geração do plano.
A validação de ExecutionStep garante que apenas as ferramentas elegíveis por grupo e estado sejam usadas.
O controlador de fluxo impõe a disponibilidade da ferramenta em tempo de execução.
As transições de estado são gerenciadas pelo Controlador de Fluxo entre os passos.

### 5. Exemplos de Configuração

#### 5.1 Configuração de Ferramentas com Grupos e Estados

```yaml
tool:
  knowledge-query:
    type: knowledge-query
    name: "Knowledge Graph Query"
    description: "Query the knowledge graph for entities and relationships"
    group: ["read-only", "knowledge", "basic"]
    state: "analysis"
    available_in_states: ["undefined", "research"]
    
  graph-update:
    type: graph-update
    name: "Graph Update"
    description: "Add or modify entities in the knowledge graph"
    group: ["write", "knowledge", "admin"]
    available_in_states: ["analysis", "modification"]
    
  text-completion:
    type: text-completion
    name: "Text Completion"
    description: "Generate text using language models"
    group: ["read-only", "text", "basic"]
    state: "undefined"
    # No available_in_states = available in all states
    
  complex-analysis:
    type: mcp-tool
    name: "Complex Analysis Tool"
    description: "Perform complex data analysis"
    group: ["advanced", "compute", "expensive"]
    state: "results"
    available_in_states: ["analysis"]
    mcp_tool_id: "analysis-server"
    
  reset-workflow:
    type: mcp-tool
    name: "Reset Workflow"
    description: "Reset to initial state"
    group: ["admin"]
    state: "undefined"
    available_in_states: ["analysis", "results"]
```

#### 5.2 Exemplos de Solicitações com Fluxos de Trabalho de Estado

**Solicitação de Pesquisa Inicial:**
```json
{
  "question": "What entities are connected to Company X?",
  "group": ["read-only", "knowledge"],
  "state": "undefined"
}
```
*Ferramentas disponíveis: knowledge-query, text-completion*
*Após knowledge-query: estado → "análise"*

**Fase de Análise:**
```json
{
  "question": "Continue analysis based on previous results",
  "group": ["advanced", "compute", "write"],
  "state": "analysis"
}
```
*Ferramentas disponíveis: complex-analysis, graph-update, reset-workflow*
*Após complex-analysis: estado → "results"*

**Fase de Resultados:**
```json
{
  "question": "What should I do with these results?",
  "group": ["admin"],
  "state": "results"
}
```
*Ferramentas disponíveis: apenas reset-workflow*
*Após reset-workflow: estado → "indefinido"*

**Exemplo de Fluxo de Trabalho - Fluxo Completo:**
1. **Início (indefinido)**: Use knowledge-query → transições para "análise"
2. **Estado de análise**: Use complex-analysis → transições para "resultados"
3. **Estado de resultados**: Use reset-workflow → transições de volta para "indefinido"
4. **Retorno ao início**: Todas as ferramentas iniciais estão disponíveis novamente

### 6. Considerações de Segurança

#### 6.1 Integração de Controle de Acesso

**Filtragem no Nível do Gateway:**
O gateway pode impor restrições de grupo com base nas permissões do usuário
Previne a elevação de privilégios através da manipulação de solicitações
O registro de auditoria inclui os grupos de ferramentas solicitados e concedidos

**Exemplo de Lógica do Gateway:**
```
user_permissions = get_user_permissions(request.user_id)
allowed_groups = user_permissions.tool_groups
requested_groups = request.group

# Validate request doesn't exceed permissions
if not is_subset(requested_groups, allowed_groups):
    reject_request("Insufficient permissions for requested tool groups")
```

#### 6.2 Auditoria e Monitoramento

**Rastreamento de Auditoria Aprimorado:**
Registrar os grupos de ferramentas solicitados e o estado inicial por solicitação
Rastrear as transições de estado e o uso de ferramentas por associação a grupos
Monitorar tentativas de acesso não autorizado a grupos e transições de estado inválidas
Alertar sobre padrões de uso de grupos incomuns ou fluxos de trabalho de estado suspeitos

### 7. Estratégia de Migração

#### 7.1 Compatibilidade com Versões Anteriores

**Fase 1: Alterações Aditivas**
Adicionar campo opcional `group` às configurações de ferramentas
Adicionar campo opcional `group` ao esquema AgentRequest
Comportamento padrão: Todas as ferramentas existentes pertencem ao grupo "default"
Solicitações existentes sem o campo de grupo usam o grupo "default"

**Comportamento Existente Preservado:**
Ferramentas sem configuração de grupo continuam a funcionar (grupo default)
Ferramentas sem configuração de estado estão disponíveis em todos os estados
Solicitações sem especificação de grupo acessam todas as ferramentas (grupo default)
Solicitações sem especificação de estado usam o estado "undefined" (todas as ferramentas disponíveis)
Nenhuma alteração disruptiva para implantações existentes

### 8. Monitoramento e Observabilidade

#### 8.1 Novas Métricas

**Uso de Grupos de Ferramentas:**
`agent_tool_group_requests_total` - Contador de solicitações por grupo
`agent_tool_group_availability` - Indicador do número de ferramentas disponíveis por grupo
`agent_filtered_tools_count` - Histograma do número de ferramentas após a filtragem por grupo + estado

**Métricas de Fluxo de Trabalho de Estado:**
`agent_state_transitions_total` - Contador de transições de estado por ferramenta
`agent_workflow_duration_seconds` - Histograma do tempo gasto em cada estado
`agent_state_availability` - Indicador do número de ferramentas disponíveis por estado

**Métricas de Segurança:**
`agent_group_access_denied_total` - Contador de acessos a grupos não autorizados
`agent_invalid_state_transition_total` - Contador de transições de estado inválidas
`agent_privilege_escalation_attempts_total` - Contador de solicitações suspeitas

#### 8.2 Melhorias de Registro (Logging)

**Registro de Solicitações:**
```json
{
  "request_id": "req-123",
  "requested_groups": ["read-only", "knowledge"],
  "initial_state": "undefined",
  "state_transitions": [
    {"tool": "knowledge-query", "from": "undefined", "to": "analysis", "timestamp": "2024-01-01T10:00:01Z"}
  ],
  "available_tools": ["knowledge-query", "text-completion"],
  "filtered_by_group": ["graph-update", "admin-tool"],
  "filtered_by_state": [],
  "execution_time": "1.2s"
}
```

### 9. Estratégia de Testes

#### 9.1 Testes Unitários

**Lógica de Filtragem de Ferramentas:**
Cálculos de interseção de grupos de teste
Lógica de filtragem baseada em estado
Verificar a atribuição padrão de grupo e estado
Testar o comportamento de grupos curinga
Validar o tratamento de grupos vazios
Testar cenários de filtragem combinada de grupo+estado

**Validação de Configuração:**
Testar o carregamento de ferramentas com várias configurações de grupo e estado
Verificar a validação de esquema para especificações inválidas de grupo e estado
Testar a compatibilidade com versões anteriores com as configurações existentes
Validar as definições e ciclos de transição de estado

#### 9.2 Testes de Integração

**Comportamento do Agente:**
Verificar se os agentes veem apenas as ferramentas filtradas por grupo+estado
Testar a execução de solicitações com várias combinações de grupos
Testar as transições de estado durante a execução do agente
Validar o tratamento de erros quando nenhuma ferramenta está disponível
Testar a progressão do fluxo de trabalho por meio de vários estados

**Testes de Segurança:**
Testar a prevenção de escalada de privilégios
Verificar a precisão do registro de auditoria
Testar a integração do gateway com as permissões do usuário

#### 9.3 Cenários de Ponta a Ponta

**Uso Multi-tenant com Fluxos de Trabalho de Estado:**
```
Scenario: Different users with different tool access and workflow states
Given: User A has "read-only" permissions, state "undefined"
  And: User B has "write" permissions, state "analysis"
When: Both request knowledge operations
Then: User A gets read-only tools available in "undefined" state
  And: User B gets write tools available in "analysis" state
  And: State transitions are tracked per user session
  And: All usage and transitions are properly audited
```

**Progressão do Estado do Fluxo de Trabalho:**
```
Scenario: Complete workflow execution
Given: Request with groups ["knowledge", "compute"] and state "undefined"
When: Agent executes knowledge-query tool (transitions to "analysis")
  And: Agent executes complex-analysis tool (transitions to "results")
  And: Agent executes reset-workflow tool (transitions to "undefined")
Then: Each step has correctly filtered available tools
  And: State transitions are logged with timestamps
  And: Final state allows initial workflow to repeat
```

### 10. Considerações de Desempenho

#### 10.1 Impacto do Carregamento de Ferramentas

**Carregamento de Configuração:**
Metadados de grupo e estado carregados uma vez na inicialização
Sobrecarga de memória mínima por ferramenta (campos adicionais)
Sem impacto no tempo de inicialização da ferramenta

**Processamento de Requisições:**
Filtragem combinada de grupo+estado ocorre uma vez por requisição
Complexidade O(n) onde n = número de ferramentas configuradas
Transições de estado adicionam uma sobrecarga mínima (atribuição de string)
Impacto insignificante para um número típico de ferramentas (< 100)

#### 10.2 Estratégias de Otimização

**Conjuntos de Ferramentas Pré-calculados:**
Armazene em cache os conjuntos de ferramentas por combinação de grupo+estado
Evite filtragem repetida para padrões comuns de grupo/estado
Troca entre memória e computação para combinações frequentemente usadas

**Carregamento Preguiçoso (Lazy Loading):**
Carregue as implementações das ferramentas somente quando necessário
Reduza o tempo de inicialização para implantações com muitas ferramentas
Registro dinâmico de ferramentas com base nos requisitos do grupo

### 11. Melhorias Futuras

#### 11.1 Atribuição Dinâmica de Grupos

**Agrupamento Contextual:**
Atribua ferramentas a grupos com base no contexto da requisição
Disponibilidade do grupo baseada no tempo (apenas horário comercial)
Restrições de grupo baseadas na carga (ferramentas caras durante baixo uso)

#### 11.2 Hierarquias de Grupos

**Estrutura de Grupo Aninhada:**
```json
{
  "knowledge": {
    "read": ["knowledge-query", "entity-search"],
    "write": ["graph-update", "entity-create"]
  }
}
```

#### 11.3 Recomendações de Ferramentas

**Sugestões Baseadas em Grupos:**
Sugerir grupos de ferramentas ideais para tipos de requisições
Aprender com padrões de uso para melhorar as recomendações
Fornecer grupos de fallback quando as ferramentas preferidas não estiverem disponíveis

### 12. Perguntas Abertas

1. **Validação de Grupos**: Nomes de grupos inválidos em requisições devem causar falhas graves ou avisos?

2. **Descoberta de Grupos**: O sistema deve fornecer uma API para listar os grupos disponíveis e suas ferramentas?

3. **Grupos Dinâmicos**: Os grupos devem ser configuráveis em tempo de execução ou apenas na inicialização?

4. **Herança de Grupos**: As ferramentas devem herdar grupos de suas categorias ou implementações pai?

5. **Monitoramento de Desempenho**: Quais métricas adicionais são necessárias para rastrear o uso de ferramentas com base em grupos de forma eficaz?

### 13. Conclusão

O sistema de grupos de ferramentas fornece:

**Segurança**: Controle de acesso granular sobre as capacidades do agente
**Desempenho**: Redução da sobrecarga de carregamento e seleção de ferramentas
**Flexibilidade**: Classificação de ferramentas multidimensional
**Compatibilidade**: Integração perfeita com arquiteturas de agentes existentes

Este sistema permite que as implementações do TrustGraph gerenciem melhor o acesso às ferramentas, aprimorem as fronteiras de segurança e otimizem o uso de recursos, mantendo total compatibilidade com versões anteriores de configurações e requisições.
