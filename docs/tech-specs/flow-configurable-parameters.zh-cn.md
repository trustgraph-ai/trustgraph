# Flow Blueprint Configurable Parameters Technical Specification

## Overview

本规范描述了 TrustGraph 中可配置参数在流程蓝图中的实现方式。参数允许用户在流程启动时自定义处理器参数，通过提供用于替换流程蓝图定义中参数占位符的值来实现。

<<<<<<< HEAD
参数通过处理器参数中的模板变量替换来实现，类似于 `{id}` 和 `{class}` 变量的工作方式，但使用用户提供的值。

该集成支持四种主要用例：

1. **模型选择**: 允许用户选择不同的 LLM 模型（例如，`gemma3:8b`、`gpt-4`、`claude-3`）用于处理器。
=======
参数通过处理器参数中的模板变量替换来工作，类似于 `{id}` 和 `{class}` 变量的工作方式，但使用用户提供的值。

该集成支持四种主要用例：

1. **模型选择**: 允许用户选择不同的 LLM 模型 (例如，`gemma3:8b`, `gpt-4`, `claude-3`) 用于处理器。
>>>>>>> 82edf2d (New md files from RunPod)
2. **资源配置**: 调整处理器参数，例如块大小、批处理大小和并发限制。
3. **行为调整**: 通过参数修改处理器行为，例如温度、最大 token 数或检索阈值。
4. **环境特定参数**: 配置每个部署的环境端点、API 密钥或区域特定 URL。

## 目标

**动态处理器配置**: 通过参数替换启用处理器参数的运行时配置。
**参数验证**: 在流程启动时提供参数的类型检查和验证。
<<<<<<< HEAD
**默认值**: 提供合理的默认值，同时允许高级用户进行覆盖。
=======
**默认值**: 支持合理的默认值，同时允许高级用户进行覆盖。
>>>>>>> 82edf2d (New md files from RunPod)
**模板替换**: Seamlessly 替换处理器参数中的参数占位符。
**UI 集成**: 通过 API 和 UI 接口提供参数输入。
**类型安全**: 确保参数类型与预期的处理器参数类型匹配。
**文档**: 在流程蓝图定义中提供自文档化的参数模式。
**向后兼容性**: 保持与不使用参数的现有流程蓝图的兼容性。

## 背景

<<<<<<< HEAD
TrustGraph 中的流程蓝图现在支持处理器参数，这些参数可以包含固定值或参数占位符。这为运行时自定义提供了机会。
=======
TrustGraph 中的流程蓝图现在支持处理器参数，这些参数可以包含固定值或参数占位符。 这为运行时自定义提供了机会。
>>>>>>> 82edf2d (New md files from RunPod)

当前处理器参数支持：
固定值：`"model": "gemma3:12b"`
参数占位符：`"model": "gemma3:{model-size}"`

本规范定义了参数的：
<<<<<<< HEAD
在流程蓝图定义中的声明方式
流程启动时的验证方式
在处理器参数中的替换方式
通过 API 和 UI 的暴露方式
=======
在流程蓝图定义中的声明
在流程启动时的验证
在处理器参数中的替换
通过 API 和 UI 的暴露
>>>>>>> 82edf2d (New md files from RunPod)

通过利用参数化的处理器参数，TrustGraph 可以：
通过使用参数进行变体，减少流程蓝图的重复。
允许用户在不修改定义的情况下调整处理器行为。
通过参数值支持环境特定的配置。
通过参数模式验证确保类型安全。

## 技术设计

### 架构

可配置参数系统需要以下技术组件：

1. **参数模式定义**
   基于 JSON Schema 的参数定义，位于流程蓝图元数据中。
   类型定义，包括字符串、数字、布尔值、枚举和对象类型。
   验证规则，包括最小值/最大值、模式和必填字段。

   模块：trustgraph-flow/trustgraph/flow/definition.py

2. **参数解析引擎**
   对模式进行运行时参数验证。
   为未指定的参数应用默认值。
   将参数注入到流程执行上下文。
   如有必要进行类型转换和转换。

   模块：trustgraph-flow/trustgraph/flow/parameter_resolver.py

3. **参数存储集成**
   从模式/配置存储中检索参数定义。
   缓存常用的参数定义。
<<<<<<< HEAD
   对其进行验证，以确保其与中心存储的模式一致。
=======
   对其进行集中存储的模式验证。
>>>>>>> 82edf2d (New md files from RunPod)

   模块：trustgraph-flow/trustgraph/flow/parameter_store.py

4. **流程启动器扩展**
   API 扩展，用于在流程启动期间接受参数值。
<<<<<<< HEAD
   参数映射解析（将流程名称映射到定义名称）。
=======
   参数映射解析 (将流程名称映射到定义名称)。
>>>>>>> 82edf2d (New md files from RunPod)
   处理无效参数组合的错误。

   模块：trustgraph-flow/trustgraph/flow/launcher.py

5. **UI 参数表单**
   从流程参数元数据动态生成表单。
<<<<<<< HEAD
   使用 `order` 字段显示参数的顺序。
   使用 `description` 字段提供参数的描述性标签。
=======
   使用 `order` 字段显示参数顺序。
   使用 `description` 字段提供描述性参数标签。
>>>>>>> 82edf2d (New md files from RunPod)
   根据参数类型定义进行输入验证。
   参数预设和模板。

   模块：trustgraph-ui/components/flow-parameters/

### 数据模型

<<<<<<< HEAD
#### 参数定义（存储在模式/配置中）

参数定义以类型为 "parameter-type" 的方式存储在模式和配置系统中。
=======
#### 参数定义 (存储在模式/配置中)

参数定义以类型 "parameter-type" 存储在模式和配置系统中。
>>>>>>> 82edf2d (New md files from RunPod)

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

#### 带有参数引用的流程蓝图

流程蓝图定义了参数元数据，包括类型引用、描述和排序：

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

`parameters` 部分将流程特定的参数名称（键）映射到包含以下内容的参数元数据对象：
`type`：对中心定义的参数定义的引用（例如，“llm-model”）
`description`：用于UI显示的易于理解的描述
`order`：参数表单的显示顺序（较小的数字首先显示）
`advanced`（可选）：布尔标志，指示是否为高级参数（默认：false）。如果设置为true，UI可能会默认隐藏此参数或将其放置在“高级”部分
<<<<<<< HEAD
`controlled-by`（可选）：控制此参数在简单模式下值的另一个参数的名称。如果指定，此参数将从控制参数继承其值，除非显式覆盖
=======
`controlled-by`（可选）：控制此参数在简单模式下值的另一个参数的名称。如果指定，此参数将继承其值来自控制参数，除非显式覆盖
>>>>>>> 82edf2d (New md files from RunPod)

这种方法允许：
在多个流程蓝图之间重用参数类型定义
集中管理和验证参数类型
流程特定的参数描述和排序
通过描述性的参数表单增强UI体验
流程中参数验证的一致性
轻松添加新的标准参数类型
通过基本/高级模式分离简化UI
相关设置的参数值继承

#### 流程启动请求

流程启动API使用流程的参数名称来接受参数：

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

<<<<<<< HEAD
注意：在这个例子中，`llm-rag-model` 没有明确提供，但会从 `llm-model` 继承值 "claude-3"，这是因为 `llm-rag-model` 与 `llm-model` 之间存在 `controlled-by` 关系。 类似地，`chunk-overlap` 可能会继承一个基于 `chunk-size` 计算的值。
=======
注意：在这个例子中，`llm-rag-model` 没有显式提供，但会从 `llm-model` 继承 "claude-3" 的值，这是因为 `llm-rag-model` 与 `llm-model` 之间存在 `controlled-by` 关系。 类似地，`chunk-overlap` 可能会继承一个基于 `chunk-size` 计算的值。
>>>>>>> 82edf2d (New md files from RunPod)

系统将执行以下操作：
1. 从流程蓝图定义中提取参数元数据
2. 将流程参数名称映射到其类型定义（例如，`llm-model` → `llm-model` 类型）
3. 解析受控关系（例如，`llm-rag-model` 从 `llm-model` 继承）
4. 验证用户提供的和继承的值是否符合参数类型定义
5. 在流程实例化期间，将解析的值替换到处理器参数中

### 实现细节

#### 参数解析过程

当启动流程时，系统执行以下参数解析步骤：

1. **流程蓝图加载**: 加载流程蓝图定义并提取参数元数据
2. **元数据提取**: 提取每个参数的 `type`、`description`、`order`、`advanced` 和 `controlled-by`，这些信息位于流程蓝图的 `parameters` 部分
3. **类型定义查找**: 对于流程蓝图中的每个参数：
<<<<<<< HEAD
   使用 `type` 字段从 schema/config 存储中检索参数类型定义
   类型定义存储在配置系统中，类型为 "parameter-type"
   每个类型定义包含参数的 schema、默认值和验证规则
=======
   使用 `type` 字段从模式/配置存储中检索参数类型定义
   类型定义存储在配置系统中，类型为 "parameter-type"
   每个类型定义包含参数的模式、默认值和验证规则
>>>>>>> 82edf2d (New md files from RunPod)
4. **默认值解析**:
   对于流程蓝图中定义的每个参数：
     检查用户是否为该参数提供了值
     如果未提供用户值，则使用参数类型定义中的 `default` 值
     构建一个完整的参数映射，其中包含用户提供的和默认值
5. **参数继承解析**（受控关系）：
   对于具有 `controlled-by` 字段的参数，检查是否已显式提供值
   如果未提供显式值，则从控制参数继承该值
   如果控制参数也无值，则从类型定义中获取默认值
   验证 `controlled-by` 关系中是否存在循环依赖
6. **验证**: 验证完整的参数集（用户提供的、默认值和继承的值）是否符合类型定义
7. **存储**: 将完整的解析后的参数集与流程实例一起存储，以进行审计
<<<<<<< HEAD
8. **模板替换**: 使用解析后的值替换处理器参数中的参数占位符
=======
8. **模板替换**: 使用解析的值替换处理器参数中的参数占位符
>>>>>>> 82edf2d (New md files from RunPod)
9. **处理器实例化**: 使用替换后的参数创建处理器

**重要的实现说明：**
流程服务必须将用户提供的参数与参数类型定义中的默认值合并
完整的参数集（包括应用的默认值）必须与流程一起存储，以进行可追溯性
<<<<<<< HEAD
参数解析发生在流程启动时间，而不是处理器实例化时间
=======
参数解析发生在流程启动时，而不是在处理器实例化时
>>>>>>> 82edf2d (New md files from RunPod)
缺少没有默认值的必需参数会导致流程启动失败，并显示清晰的错误消息

#### 具有 controlled-by 的参数继承

`controlled-by` 字段启用参数值继承，这对于简化用户界面同时保持灵活性非常有用：

**示例场景：**
`llm-model` 参数控制主要的 LLM 模型
`llm-rag-model` 参数具有 `"controlled-by": "llm-model"`
在简单模式下，将 `llm-model` 设置为 "gpt-4" 会自动将 `llm-rag-model` 也设置为 "gpt-4"
在高级模式下，用户可以覆盖 `llm-rag-model` 并使用不同的值

**解析规则：**
1. 如果参数具有显式提供的值，则使用该值
2. 如果没有显式值且 `controlled-by` 已设置，则使用控制参数的值
3. 如果控制参数没有值，则回退到类型定义中的默认值
4. `controlled-by` 关系中的循环依赖会导致验证错误

**UI 行为：**
在基本/简单模式下：具有 `controlled-by` 的参数可能被隐藏或显示为只读，并显示继承的值
在高级模式下：显示所有参数，并且可以单独配置
当控制参数更改时，依赖参数会自动更新，除非显式覆盖

#### Pulsar 集成

1. **启动流程操作**
   Pulsar 启动流程操作需要接受一个 `parameters` 字段，该字段包含参数值的映射
<<<<<<< HEAD
   Pulsar 启动流程请求的 schema 必须更新为包含可选的 `parameters` 字段
=======
   Pulsar 用于启动流程的请求模式必须更新为包含可选的 `parameters` 字段
>>>>>>> 82edf2d (New md files from RunPod)
   示例请求：
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

2. **获取流程操作**
<<<<<<< HEAD
   必须更新 Pulsar 模式，以包含 `parameters` 字段，用于获取流程的响应。
=======
   Pulsar 用于获取流程响应的 schema 必须更新，以包含 `parameters` 字段。
>>>>>>> 82edf2d (New md files from RunPod)
   这允许客户端检索在启动流程时使用的参数值。
   示例响应：
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

#### 流程服务实现

流程配置服务 (`trustgraph-flow/trustgraph/config/service/flow.py`) 需要以下增强：

1. **参数解析功能**
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

   此函数应该：
   从流程蓝图的 `parameters` 部分提取参数元数据
   对于每个参数，从配置存储中获取其类型定义
   为任何未由用户提供的参数应用默认值
   处理 `controlled-by` 继承关系
   返回完整的参数集

2. **修改后的 `handle_start_flow` 方法**
   在加载流程蓝图后调用 `resolve_parameters`
   使用完整的解析后的参数集进行模板替换
   将完整的参数集（不仅仅是用户提供的）与流程一起存储
   验证所有必需的参数是否具有值

3. **参数类型获取**
   参数类型定义存储在配置中，类型为 "parameter-type"
   每个类型定义包含模式、默认值和验证规则
   缓存常用的参数类型以减少配置查找

#### 配置系统集成

3. **流程对象存储**
   当流程组件在配置管理器中向配置系统添加流程时，流程对象必须包含解析后的参数值
<<<<<<< HEAD
   配置管理器需要同时存储原始的用户提供的参数和解析后的值（已应用默认值）
=======
   配置管理器需要存储原始的用户提供的参数以及解析后的值（已应用默认值）
>>>>>>> 82edf2d (New md files from RunPod)
   配置系统中的流程对象应包含：
     `parameters`: 用于流程的最终解析后的参数值

#### CLI 集成

4. **库 CLI 命令**
   启动流程的 CLI 命令需要参数支持：
     通过命令行标志或配置文件接受参数值
     在提交之前，根据流程蓝图定义验证参数
     支持参数文件输入（JSON/YAML），用于复杂的参数集

   显示流程的 CLI 命令需要显示参数信息：
     显示启动流程时使用的参数值
     显示流程蓝图的可用参数
     显示参数验证模式和默认值

#### 处理器基础类集成

5. **ParameterSpec 支持**
   处理器基础类需要支持通过现有的 ParametersSpec 机制进行参数替换
   如果需要，应增强 ParametersSpec 类（位于与 ConsumerSpec 和 ProducerSpec 相同的模块中），以支持参数模板替换
   处理器应能够调用 ParametersSpec 来使用在流程启动时解析的参数值配置其参数
   ParametersSpec 的实现需要：
     接受包含参数占位符（例如，`{model}`，`{temperature}`）的参数配置
     在实例化处理器时，支持运行时参数替换
     验证替换后的值是否符合预期的类型和约束
     为缺失或无效的参数引用提供错误处理

#### 替换规则

参数使用格式 `{parameter-name}` 在处理器参数中
<<<<<<< HEAD
参数名称与流程的 `parameters` 部分中的键匹配
=======
参数名称在参数中与流程的 `parameters` 部分中的键匹配
>>>>>>> 82edf2d (New md files from RunPod)
替换操作与 `{id}` 和 `{class}` 替换同时进行
无效的参数引用会导致启动时出错
基于中心存储的参数定义进行类型验证
**重要提示**：所有参数值都以字符串形式存储和传输
  数字转换为字符串（例如，`0.7` 变为 `"0.7"`）
  布尔值转换为小写字符串（例如，`true` 变为 `"true"`）
  这是由 Pulsar 模式要求的，该模式定义了 `parameters = Map(String())`

示例解析：
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

## 测试策略

用于参数模式验证的单元测试
用于处理器参数中参数替换的集成测试
用于使用不同参数值启动流程的端到端测试
用于参数表单生成和验证的 UI 测试
用于具有许多参数的流程的性能测试
边界情况：缺少参数、无效类型、未定义的参数引用

## 迁移计划

<<<<<<< HEAD
1. 系统应继续支持未声明参数的流程蓝图。
   2. 系统应继续支持未指定参数的流程：
=======
1. 系统应继续支持未声明任何参数的流程蓝图。
   2. 系统应继续支持未指定任何参数的流程：
>>>>>>> 82edf2d (New md files from RunPod)
这适用于没有参数的流程，以及具有参数的流程（它们具有默认值）。
   
   (它们有默认值)。

## 开放问题

问：参数是否应该支持复杂的嵌套对象，还是仅限于简单类型？
答：参数值将被字符串编码，我们可能更倾向于
   使用字符串。

<<<<<<< HEAD
问：是否允许在队列名称中使用参数占位符，还是仅在
=======
问：是否允许在队列名称中使用参数占位符，或者仅在
>>>>>>> 82edf2d (New md files from RunPod)
   参数中使用？
答：仅在参数中使用，以避免奇怪的注入和边缘情况。

问：如何处理参数名称与系统变量（如
   `id` 和 `class`）之间的冲突？
答：在启动流程时，指定 id 和 class 是无效的。

问：我们是否应该支持计算参数（从其他参数派生）？
答：仅进行字符串替换，以避免奇怪的注入和边缘情况。

<<<<<<< HEAD
## 引用
=======
## 参考文献
>>>>>>> 82edf2d (New md files from RunPod)

JSON Schema 规范：https://json-schema.org/
流程蓝图定义规范：docs/tech-specs/flow-class-definition.md
