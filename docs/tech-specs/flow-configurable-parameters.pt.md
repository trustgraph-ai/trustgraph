# Especificação Técnica de Parâmetros Configuráveis para Flow Blueprint

## Visão Geral

Esta especificação descreve a implementação de parâmetros configuráveis para flow blueprints no TrustGraph. Os parâmetros permitem que os usuários personalizem os parâmetros do processador no momento da execução do fluxo, fornecendo valores que substituem os espaços reservados de parâmetros na definição do flow blueprint.

Os parâmetros funcionam por meio da substituição de variáveis de modelo nos parâmetros do processador, de forma semelhante a como as variáveis `{id}` e `{class}` funcionam, mas com valores fornecidos pelo usuário.

A integração suporta quatro casos de uso principais:

1. **Seleção de Modelo**: Permitindo que os usuários escolham diferentes modelos LLM (por exemplo, `gemma3:8b`, `gpt-4`, `claude-3`) para processadores.
2. **Configuração de Recursos**: Ajustando parâmetros do processador, como tamanhos de lote, tamanhos de lote e limites de concorrência.
3. **Ajuste de Comportamento**: Modificando o comportamento do processador por meio de parâmetros como temperatura, max-tokens ou limites de recuperação.
4. **Parâmetros Específicos do Ambiente**: Configurando endpoints, chaves de API ou URLs específicas da região para cada implantação.

## Objetivos

**Configuração Dinâmica do Processador**: Permitir a configuração em tempo de execução dos parâmetros do processador por meio da substituição de parâmetros.
**Validação de Parâmetros**: Fornecer verificação de tipo e validação para parâmetros no momento da execução do fluxo.
**Valores Padrão**: Suportar valores padrão sensatos, permitindo a substituição para usuários avançados.
**Substituição de Modelo**: Substituir perfeitamente os espaços reservados de parâmetros nos parâmetros do processador.
**Integração com a Interface do Usuário**: Permitir a entrada de parâmetros por meio de interfaces de API e de interface do usuário.
**Segurança de Tipo**: Garantir que os tipos de parâmetros correspondam aos tipos de parâmetros do processador esperados.
**Documentação**: Esquemas de parâmetros autoexplicativos dentro das definições do flow blueprint.
**Compatibilidade com Versões Anteriores**: Manter a compatibilidade com flow blueprints existentes que não usam parâmetros.

## Contexto

Flow blueprints no TrustGraph agora suportam parâmetros de processador que podem conter valores fixos ou espaços reservados de parâmetros. Isso cria uma oportunidade para personalização em tempo de execução.

Os parâmetros de processador atuais suportam:
Valores fixos: `"model": "gemma3:12b"`
Espaços reservados de parâmetros: `"model": "gemma3:{model-size}"`

Esta especificação define como os parâmetros são:
Declarados em definições de flow blueprint.
Validados quando os fluxos são iniciados.
Substituídos em parâmetros do processador.
Expostos por meio de APIs e da interface do usuário.

Ao aproveitar os parâmetros de processador parametrizados, o TrustGraph pode:
Reduzir a duplicação de flow blueprints, usando parâmetros para variações.
Permitir que os usuários ajustem o comportamento do processador sem modificar as definições.
Suportar configurações específicas do ambiente por meio de valores de parâmetro.
Manter a segurança de tipo por meio da validação do esquema de parâmetro.

## Design Técnico

### Arquitetura

O sistema de parâmetros configuráveis requer os seguintes componentes técnicos:

1. **Definição de Esquema de Parâmetro**
   Definições de parâmetros baseadas em JSON Schema dentro dos metadados do flow blueprint.
   Definições de tipo, incluindo string, número, booleano, enum e tipos de objeto.
   Regras de validação, incluindo valores mínimo/máximo, padrões e campos obrigatórios.

   Módulo: trustgraph-flow/trustgraph/flow/definition.py

2. **Motor de Resolução de Parâmetros**
   Validação de parâmetros em tempo de execução contra o esquema.
   Aplicação de valores padrão para parâmetros não especificados.
   Injeção de parâmetros no contexto de execução do fluxo.
   Coerção e conversão de tipo, conforme necessário.

   Módulo: trustgraph-flow/trustgraph/flow/parameter_resolver.py

3. **Integração com o Armazenamento de Parâmetros**
   Recuperação de definições de parâmetros do armazenamento de esquema/configuração.
   Cache de definições de parâmetros frequentemente usadas.
   Validação contra esquemas armazenados centralmente.

   Módulo: trustgraph-flow/trustgraph/flow/parameter_store.py

4. **Extensões do Lançador de Fluxo**
   Extensões de API para aceitar valores de parâmetro durante o lançamento do fluxo.
   Resolução de mapeamento de parâmetros (nomes de fluxo para nomes de definição).
   Tratamento de erros para combinações de parâmetros inválidas.

   Módulo: trustgraph-flow/trustgraph/flow/launcher.py

<<<<<<< HEAD
5. **Formulários de Parâmetro da Interface do Usuário**
   Geração dinâmica de formulários a partir de metadados de parâmetros do fluxo.
   Exibição ordenada de parâmetros usando o campo `order`.
   Rótulos de parâmetros descritivos usando o campo `description`.
=======
5. **Formulários de Parâmetros da Interface do Usuário**
   Geração dinâmica de formulários a partir de metadados de parâmetros do fluxo.
   Exibição ordenada de parâmetros usando o campo `order`.
   Rótulos descritivos de parâmetros usando o campo `description`.
>>>>>>> 82edf2d (New md files from RunPod)
   Validação de entrada contra as definições de tipo de parâmetro.
   Predefinições e modelos de parâmetros.

   Módulo: trustgraph-ui/components/flow-parameters/

### Modelos de Dados

#### Definições de Parâmetro (Armazenadas no Esquema/Configuração)

As definições de parâmetros são armazenadas centralmente no sistema de esquema e configuração com o tipo "parameter-type":

```json
{
  "llm-model": {
    "type": "string",
    "description": "LLM model to use",
    "default": "gpt-4",
    "enum": [
      {
        "id": "gpt-4",
        "description": "OpenAI GPT-4 (Most Capable)"
      },
      {
        "id": "gpt-3.5-turbo",
        "description": "OpenAI GPT-3.5 Turbo (Fast & Efficient)"
      },
      {
        "id": "claude-3",
        "description": "Anthropic Claude 3 (Thoughtful & Safe)"
      },
      {
        "id": "gemma3:8b",
        "description": "Google Gemma 3 8B (Open Source)"
      }
    ],
    "required": false
  },
  "model-size": {
    "type": "string",
    "description": "Model size variant",
    "default": "8b",
    "enum": ["2b", "8b", "12b", "70b"],
    "required": false
  },
  "temperature": {
    "type": "number",
    "description": "Model temperature for generation",
    "default": 0.7,
    "minimum": 0.0,
    "maximum": 2.0,
    "required": false
  },
  "chunk-size": {
    "type": "integer",
    "description": "Document chunk size",
    "default": 512,
    "minimum": 128,
    "maximum": 2048,
    "required": false
  }
}
```

#### Diagrama de fluxo com referências de parâmetros

Os diagramas de fluxo definem metadados de parâmetros com referências de tipo, descrições e ordem:

```json
{
  "flow_class": "document-analysis",
  "parameters": {
    "llm-model": {
      "type": "llm-model",
      "description": "Primary LLM model for text completion",
      "order": 1
    },
    "llm-rag-model": {
      "type": "llm-model",
      "description": "LLM model for RAG operations",
      "order": 2,
      "advanced": true,
      "controlled-by": "llm-model"
    },
    "llm-temperature": {
      "type": "temperature",
      "description": "Generation temperature for creativity control",
      "order": 3,
      "advanced": true
    },
    "chunk-size": {
      "type": "chunk-size",
      "description": "Document chunk size for processing",
      "order": 4,
      "advanced": true
    },
    "chunk-overlap": {
      "type": "integer",
      "description": "Overlap between document chunks",
      "order": 5,
      "advanced": true,
      "controlled-by": "chunk-size"
    }
  },
  "class": {
    "text-completion:{class}": {
      "request": "non-persistent://tg/request/text-completion:{class}",
      "response": "non-persistent://tg/response/text-completion:{class}",
      "parameters": {
        "model": "{llm-model}",
        "temperature": "{llm-temperature}"
      }
    },
    "rag-completion:{class}": {
      "request": "non-persistent://tg/request/rag-completion:{class}",
      "response": "non-persistent://tg/response/rag-completion:{class}",
      "parameters": {
        "model": "{llm-rag-model}",
        "temperature": "{llm-temperature}"
      }
    }
  },
  "flow": {
    "chunker:{id}": {
      "input": "persistent://tg/flow/chunk:{id}",
      "output": "persistent://tg/flow/chunk-load:{id}",
      "parameters": {
        "chunk_size": "{chunk-size}",
        "chunk_overlap": "{chunk-overlap}"
      }
    }
  }
}
```

A seção `parameters` mapeia nomes de parâmetros específicos do fluxo (chaves) para objetos de metadados de parâmetros que contêm:
`type`: Referência à definição de parâmetro definida centralmente (por exemplo, "llm-model")
`description`: Descrição legível por humanos para exibição na interface do usuário
`order`: Ordem de exibição para formulários de parâmetros (números menores aparecem primeiro)
`advanced` (opcional): Sinalizador booleano que indica se este é um parâmetro avançado (padrão: falso). Quando definido como verdadeiro, a interface do usuário pode ocultar este parâmetro por padrão ou colocá-lo em uma seção "Avançado"
`controlled-by` (opcional): Nome de outro parâmetro que controla o valor deste parâmetro quando no modo simples. Quando especificado, este parâmetro herda seu valor do parâmetro de controle, a menos que seja explicitamente substituído

Esta abordagem permite:
Definições de tipos de parâmetros reutilizáveis em vários modelos de fluxo
Gerenciamento e validação centralizados de tipos de parâmetros
Descrições e ordenação de parâmetros específicos do fluxo
Experiência de interface do usuário aprimorada com formulários de parâmetros descritivos
Validação consistente de parâmetros em todos os fluxos
Adição fácil de novos tipos de parâmetros padrão
Interface do usuário simplificada com separação de modo básico/avançado
Herança de valores de parâmetros para configurações relacionadas

#### Solicitação de Inicialização do Fluxo

A API de inicialização do fluxo aceita parâmetros usando os nomes de parâmetros do fluxo:

```json
{
  "flow_class": "document-analysis",
  "flow_id": "customer-A-flow",
  "parameters": {
    "llm-model": "claude-3",
    "llm-temperature": 0.5,
    "chunk-size": 1024
  }
}
```

Nota: Neste exemplo, `llm-rag-model` não é fornecido explicitamente, mas herdará o valor "claude-3" de `llm-model` devido à sua relação `controlled-by`. Da mesma forma, `chunk-overlap` pode herdar um valor calculado com base em `chunk-size`.

O sistema irá:
<<<<<<< HEAD
1. Extrair metadados de parâmetros da definição do blueprint do fluxo
2. Mapear os nomes dos parâmetros do fluxo para suas definições de tipo (por exemplo, `llm-model` → `llm-model` tipo)
3. Resolver as relações "controlado por" (por exemplo, `llm-rag-model` herda de `llm-model`)
4. Validar os valores fornecidos pelo usuário e os valores herdados em relação às definições de tipo dos parâmetros
5. Substituir os valores resolvidos nos parâmetros do processador durante a instanciação do fluxo
=======
1. Extrair metadados de parâmetros da definição do fluxo.
2. Mapear os nomes dos parâmetros do fluxo para suas definições de tipo (por exemplo, `llm-model` → `llm-model` tipo).
3. Resolver relações de dependência (por exemplo, `llm-rag-model` herda de `llm-model`).
4. Validar os valores fornecidos pelo usuário e os valores herdados em relação às definições de tipo dos parâmetros.
5. Substituir os valores resolvidos nos parâmetros do processador durante a instanciação do fluxo.
>>>>>>> 82edf2d (New md files from RunPod)

### Detalhes da Implementação

#### Processo de Resolução de Parâmetros

Quando um fluxo é iniciado, o sistema executa as seguintes etapas de resolução de parâmetros:

<<<<<<< HEAD
1. **Carregamento do Blueprint do Fluxo**: Carregar a definição do blueprint do fluxo e extrair os metadados dos parâmetros
2. **Extração de Metadados**: Extrair `type`, `description`, `order`, `advanced` e `controlled-by` para cada parâmetro definido na seção `parameters` do blueprint do fluxo
3. **Consulta da Definição de Tipo**: Para cada parâmetro no blueprint do fluxo:
   Recuperar a definição de tipo do parâmetro do armazenamento de esquema/configuração usando o campo `type`
   As definições de tipo são armazenadas com o tipo "parameter-type" no sistema de configuração
   Cada definição de tipo contém o esquema do parâmetro, o valor padrão e as regras de validação
4. **Resolução do Valor Padrão**:
   Para cada parâmetro definido no blueprint do fluxo:
     Verificar se o usuário forneceu um valor para este parâmetro
     Se nenhum valor do usuário for fornecido, usar o valor `default` da definição de tipo do parâmetro
     Criar um mapa de parâmetros completo contendo tanto os valores fornecidos pelo usuário quanto os valores padrão
5. **Resolução de Herança de Parâmetros** (relações "controlado por"):
   Para parâmetros com o campo `controlled-by`, verificar se um valor foi fornecido explicitamente
   Se nenhum valor explícito for fornecido, herdar o valor do parâmetro de controle
   Se o parâmetro de controle também não tiver valor, usar o padrão da definição de tipo
   Validar que não existam dependências circulares nas relações `controlled-by`
6. **Validação**: Validar o conjunto completo de parâmetros (fornecidos pelo usuário, padrões e herdados) em relação às definições de tipo
7. **Armazenamento**: Armazenar o conjunto completo de parâmetros resolvidos com a instância do fluxo para auditoria
8. **Substituição de Modelos**: Substituir os espaços reservados de parâmetros nos parâmetros do processador com os valores resolvidos
9. **Instanciação do Processador**: Criar processadores com os parâmetros substituídos

**Notas Importantes de Implementação:**
O serviço de fluxo DEVE mesclar os parâmetros fornecidos pelo usuário com os padrões das definições de tipo de parâmetro
O conjunto completo de parâmetros (incluindo os padrões aplicados) DEVE ser armazenado com o fluxo para rastreabilidade
A resolução de parâmetros ocorre no início do fluxo, não no momento da instanciação do processador
Parâmetros obrigatórios sem padrões DEVE causar a falha no início do fluxo com uma mensagem de erro clara

#### Herança de Parâmetros com "controlado-por"

O campo `controlled-by` permite a herança de valores de parâmetros, o que é particularmente útil para simplificar as interfaces do usuário, mantendo a flexibilidade:

**Cenário de Exemplo**:
O parâmetro `llm-model` controla o modelo LLM primário
O parâmetro `llm-rag-model` tem `"controlled-by": "llm-model"`
No modo simples, definir `llm-model` para "gpt-4" define automaticamente `llm-rag-model` para "gpt-4" também
No modo avançado, os usuários podem substituir `llm-rag-model` com um valor diferente

**Regras de Resolução**:
1. Se um parâmetro tiver um valor fornecido explicitamente, use esse valor
2. Se não houver valor explícito e `controlled-by` estiver definido, use o valor do parâmetro de controle
3. Se o parâmetro de controle não tiver valor, use o padrão da definição de tipo
4. Dependências circulares nas relações `controlled-by` resultam em um erro de validação

**Comportamento da IU**:
No modo básico/simples: Parâmetros com `controlled-by` podem ser ocultos ou exibidos como somente leitura com valor herdado
No modo avançado: Todos os parâmetros são exibidos e podem ser configurados individualmente
Quando um parâmetro de controle é alterado, os parâmetros dependentes são atualizados automaticamente, a menos que sejam explicitamente substituídos
=======
1. **Carregamento da Definição do Fluxo**: Carregar a definição do fluxo e extrair os metadados dos parâmetros.
2. **Extração de Metadados**: Extrair `type`, `description`, `order`, `advanced` e `controlled-by` para cada parâmetro definido na seção `parameters` da definição do fluxo.
3. **Consulta da Definição de Tipo**: Para cada parâmetro na definição do fluxo:
   Recuperar a definição de tipo do parâmetro do armazenamento de esquema/configuração usando o campo `type`.
   As definições de tipo são armazenadas com o tipo "parameter-type" no sistema de configuração.
   Cada definição de tipo contém o esquema do parâmetro, o valor padrão e as regras de validação.
4. **Resolução do Valor Padrão**:
   Para cada parâmetro definido na definição do fluxo:
     Verificar se o usuário forneceu um valor para este parâmetro.
     Se nenhum valor do usuário for fornecido, usar o valor `default` da definição de tipo do parâmetro.
     Criar um mapa de parâmetros completo contendo tanto os valores fornecidos pelo usuário quanto os valores padrão.
5. **Resolução de Herança de Parâmetros** (relações de dependência):
   Para parâmetros com o campo `controlled-by`, verificar se um valor foi fornecido explicitamente.
   Se nenhum valor explícito for fornecido, herdar o valor do parâmetro de controle.
   Se o parâmetro de controle também não tiver valor, usar o padrão da definição de tipo.
   Validar que não existam dependências circulares nas relações `controlled-by`.
6. **Validação**: Validar o conjunto completo de parâmetros (fornecidos pelo usuário, padrões e herdados) em relação às definições de tipo.
7. **Armazenamento**: Armazenar o conjunto completo de parâmetros resolvidos com a instância do fluxo para auditoria.
8. **Substituição de Marcadores**: Substituir os marcadores de parâmetros nos parâmetros do processador pelos valores resolvidos.
9. **Instanciação do Processador**: Criar processadores com os parâmetros substituídos.

**Notas Importantes de Implementação:**
O serviço de fluxo DEVE mesclar os parâmetros fornecidos pelo usuário com os padrões das definições de tipo de parâmetro.
O conjunto completo de parâmetros (incluindo os padrões aplicados) DEVE ser armazenado com o fluxo para rastreabilidade.
A resolução de parâmetros ocorre no início do fluxo, não no momento da instanciação do processador.
Parâmetros obrigatórios sem padrões DEVE causar a falha no início do fluxo com uma mensagem de erro clara.

#### Herança de Parâmetros com dependência

O campo `controlled-by` permite a herança de valores de parâmetros, o que é particularmente útil para simplificar interfaces de usuário, mantendo a flexibilidade:

**Cenário de Exemplo**:
O parâmetro `llm-model` controla o modelo LLM primário.
O parâmetro `llm-rag-model` tem o valor `"controlled-by": "llm-model"`.
No modo simples, definir `llm-model` para "gpt-4" define automaticamente `llm-rag-model` para "gpt-4" também.
No modo avançado, os usuários podem substituir `llm-rag-model` com um valor diferente.

**Regras de Resolução**:
1. Se um parâmetro tiver um valor fornecido explicitamente, use esse valor.
2. Se não houver valor explícito e `controlled-by` estiver definido, use o valor do parâmetro de controle.
3. Se o parâmetro de controle não tiver valor, use o padrão da definição de tipo.
4. Dependências circulares nas relações `controlled-by` resultam em um erro de validação.

**Comportamento da Interface do Usuário**:
No modo básico/simples: Parâmetros com `controlled-by` podem ser ocultos ou exibidos como somente leitura com valor herdado.
No modo avançado: Todos os parâmetros são exibidos e podem ser configurados individualmente.
Quando um parâmetro de controle é alterado, os parâmetros dependentes são atualizados automaticamente, a menos que sejam explicitamente substituídos.
>>>>>>> 82edf2d (New md files from RunPod)

#### Integração com Pulsar

1. **Operação Start-Flow**
<<<<<<< HEAD
   A operação start-flow do Pulsar precisa aceitar um campo `parameters` contendo um mapa de valores de parâmetros
   O esquema do Pulsar para a solicitação start-flow deve ser atualizado para incluir o campo opcional `parameters`
=======
   A operação start-flow do Pulsar precisa aceitar um campo `parameters` contendo um mapa de valores de parâmetros.
   O esquema do Pulsar para a solicitação start-flow deve ser atualizado para incluir o campo opcional `parameters`.
>>>>>>> 82edf2d (New md files from RunPod)
   Exemplo de solicitação:
   ```json
   {
     "flow_class": "document-analysis",
     "flow_id": "customer-A-flow",
     "parameters": {
       "model": "claude-3",
       "size": "12b",
       "temp": 0.5,
       "chunk": 1024
     }
   }
   ```

2. **Operação Get-Flow**
   O esquema Pulsar para a resposta do get-flow deve ser atualizado para incluir o campo `parameters`
   Isso permite que os clientes recuperem os valores dos parâmetros que foram usados quando o fluxo foi iniciado.
   Exemplo de resposta:
   ```json
   {
     "flow_id": "customer-A-flow",
     "flow_class": "document-analysis",
     "status": "running",
     "parameters": {
       "model": "claude-3",
       "size": "12b",
       "temp": 0.5,
       "chunk": 1024
     }
   }
   ```

#### Implementação do Serviço de Fluxo

O serviço de configuração de fluxo (`trustgraph-flow/trustgraph/config/service/flow.py`) requer as seguintes melhorias:

1. **Função de Resolução de Parâmetros**
   ```python
   async def resolve_parameters(self, flow_class, user_params):
       """
       Resolve parameters by merging user-provided values with defaults.

       Args:
           flow_class: The flow blueprint definition dict
           user_params: User-provided parameters dict

       Returns:
           Complete parameter dict with user values and defaults merged
       """
   ```

   Esta função deve:
   Extrair metadados de parâmetros da seção `parameters` do blueprint do fluxo
   Para cada parâmetro, buscar a definição de tipo no armazenamento de configuração
   Aplicar valores padrão para quaisquer parâmetros não fornecidos pelo usuário
   Lidar com relacionamentos de herança `controlled-by`
   Retornar o conjunto completo de parâmetros

2. **Método `handle_start_flow` Modificado**
   Chamar `resolve_parameters` após carregar o blueprint do fluxo
<<<<<<< HEAD
   Usar o conjunto completo de parâmetros resolvidos para substituição de modelo
=======
   Usar o conjunto completo de parâmetros resolvidos para a substituição de modelo
>>>>>>> 82edf2d (New md files from RunPod)
   Armazenar o conjunto completo de parâmetros (não apenas os fornecidos pelo usuário) com o fluxo
   Validar que todos os parâmetros obrigatórios tenham valores

3. **Busca de Tipo de Parâmetro**
   As definições de tipo de parâmetro são armazenadas na configuração com o tipo "parameter-type"
   Cada definição de tipo contém esquema, valor padrão e regras de validação
   Armazenar em cache os tipos de parâmetro frequentemente usados para reduzir as consultas à configuração

#### Integração com o Sistema de Configuração

3. **Armazenamento de Objetos de Fluxo**
   Quando um fluxo é adicionado ao sistema de configuração pelo componente de fluxo no gerenciador de configuração, o objeto de fluxo deve incluir os valores de parâmetros resolvidos
   O gerenciador de configuração precisa armazenar tanto os parâmetros originais fornecidos pelo usuário quanto os valores resolvidos (com os padrões aplicados)
   Os objetos de fluxo no sistema de configuração devem incluir:
<<<<<<< HEAD
     `parameters`: Os valores finais de parâmetros resolvidos usados para o fluxo
=======
     `parameters`: Os valores de parâmetros resolvidos finais usados para o fluxo
>>>>>>> 82edf2d (New md files from RunPod)

#### Integração com a CLI

4. **Comandos da CLI da Biblioteca**
   Os comandos da CLI que iniciam fluxos precisam de suporte a parâmetros:
     Aceitar valores de parâmetros por meio de flags de linha de comando ou arquivos de configuração
<<<<<<< HEAD
     Validar parâmetros em relação às definições do blueprint do fluxo antes da submissão
=======
     Validar os parâmetros em relação às definições do blueprint do fluxo antes da submissão
>>>>>>> 82edf2d (New md files from RunPod)
     Suportar a entrada de arquivos de parâmetros (JSON/YAML) para conjuntos de parâmetros complexos

   Os comandos da CLI que mostram fluxos precisam exibir informações de parâmetros:
     Mostrar os valores de parâmetros usados quando o fluxo foi iniciado
     Exibir os parâmetros disponíveis para um blueprint de fluxo
     Mostrar os esquemas e padrões de validação de parâmetros

#### Integração com a Classe Base do Processador

5. **Suporte a ParameterSpec**
<<<<<<< HEAD
   As classes base do processador precisam suportar a substituição de parâmetros por meio do mecanismo existente ParametersSpec
=======
   As classes base do processador precisam suportar a substituição de parâmetros por meio do mecanismo ParametersSpec existente
>>>>>>> 82edf2d (New md files from RunPod)
   A classe ParametersSpec (localizada no mesmo módulo que ConsumerSpec e ProducerSpec) deve ser aprimorada, se necessário, para suportar a substituição de modelos de parâmetros
   Os processadores devem ser capazes de invocar ParametersSpec para configurar seus parâmetros com valores de parâmetros resolvidos no momento da inicialização do fluxo
   A implementação de ParametersSpec precisa:
     Aceitar configurações de parâmetros que contenham espaços reservados de parâmetros (por exemplo, `{model}`, `{temperature}`)
     Suportar a substituição de parâmetros em tempo de execução quando o processador é instanciado
     Validar que os valores substituídos correspondam aos tipos e restrições esperados
     Fornecer tratamento de erros para referências de parâmetros ausentes ou inválidos

#### Regras de Substituição

Os parâmetros usam o formato `{parameter-name}` nos parâmetros do processador
Os nomes dos parâmetros nos parâmetros correspondem às chaves na seção `parameters` do fluxo
A substituição ocorre juntamente com a substituição de `{id}` e `{class}`
Referências de parâmetros inválidas resultam em erros no momento da inicialização
A validação de tipo ocorre com base na definição de parâmetro armazenada centralmente
**IMPORTANTE**: Todos os valores de parâmetros são armazenados e transmitidos como strings
  Os números são convertidos em strings (por exemplo, `0.7` se torna `"0.7"`)
  Os booleanos são convertidos em strings em letras minúsculas (por exemplo, `true` se torna `"true"`)
  Isso é necessário pelo esquema do Pulsar que define `parameters = Map(String())`

Exemplo de resolução:
```
Flow parameter mapping: "model": "llm-model"
Processor parameter: "model": "{model}"
User provides: "model": "gemma3:8b"
Final parameter: "model": "gemma3:8b"

Example with type conversion:
Parameter type default: 0.7 (number)
Stored in flow: "0.7" (string)
Substituted in processor: "0.7" (string)
```

## Estratégia de Testes

<<<<<<< HEAD
Testes unitários para validação do esquema de parâmetros
Testes de integração para substituição de parâmetros nos parâmetros do processador
Testes de ponta a ponta para iniciar fluxos com diferentes valores de parâmetros
Testes de interface do usuário para geração e validação de formulários de parâmetros
Testes de desempenho para fluxos com muitos parâmetros
Casos extremos: parâmetros ausentes, tipos inválidos, referências de parâmetros indefinidos
=======
Testes unitários para validação do esquema de parâmetros.
Testes de integração para substituição de parâmetros nos parâmetros do processador.
Testes de ponta a ponta para iniciar fluxos com diferentes valores de parâmetros.
Testes de interface do usuário para geração e validação de formulários de parâmetros.
Testes de desempenho para fluxos com muitos parâmetros.
Casos de borda: parâmetros ausentes, tipos inválidos, referências de parâmetros indefinidos.
>>>>>>> 82edf2d (New md files from RunPod)

## Plano de Migração

1. O sistema deve continuar a suportar modelos de fluxo sem parâmetros
   declarados.
2. O sistema deve continuar a suportar fluxos sem parâmetros especificados:
   Isso funciona para fluxos sem parâmetros e para fluxos com parâmetros
   (eles têm valores padrão).

## Perguntas Abertas

P: Os parâmetros devem suportar objetos aninhados complexos ou devem se limitar a tipos simples?
R: Os valores dos parâmetros serão codificados como strings, provavelmente queremos
   restringir a strings.

P: Os espaços reservados de parâmetros devem ser permitidos em nomes de filas ou apenas em
   parâmetros?
<<<<<<< HEAD
R: Apenas em parâmetros para evitar injeções estranhas e casos extremos.
=======
R: Apenas em parâmetros para remover injeções estranhas e casos de borda.
>>>>>>> 82edf2d (New md files from RunPod)

P: Como lidar com conflitos entre nomes de parâmetros e variáveis do sistema, como
   `id` e `class`?
R: Não é válido especificar "id" e "class" ao iniciar um fluxo.

P: Devemos suportar parâmetros calculados (derivados de outros parâmetros)?
<<<<<<< HEAD
R: Apenas substituição de strings para evitar injeções estranhas e casos extremos.
=======
R: Apenas substituição de strings para remover injeções estranhas e casos de borda.
>>>>>>> 82edf2d (New md files from RunPod)

## Referências

Especificação do Esquema JSON: https://json-schema.org/
Especificação da Definição do Modelo de Fluxo: docs/tech-specs/flow-class-definition.md
