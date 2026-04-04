# Especificación de Argumentos para la Herramienta MCP

## Visión General
**Nombre de la característica**: Soporte para Argumentos de la Herramienta MCP
**Autor**: Asistente de Código Claude
**Fecha**: 21/08/2025
**Estado**: Finalizado

### Resumen Ejecutivo

Permitir que los agentes ReACT invoquen las herramientas MCP (Protocolo de Contexto del Modelo) con argumentos definidos correctamente, agregando soporte para la especificación de argumentos a las configuraciones de las herramientas MCP, de manera similar a como funcionan actualmente las herramientas de plantillas de prompts.

### Declaración del Problema

Actualmente, las herramientas MCP en el marco de agentes ReACT no pueden especificar sus argumentos esperados. El método `McpToolImpl.get_arguments()` devuelve una lista vacía, lo que obliga a los LLMs a adivinar la estructura de parámetros correcta basándose únicamente en los nombres y las descripciones de las herramientas. Esto conduce a:
- Invocaciones de herramientas poco fiables debido a la adivinación de parámetros
- Mala experiencia de usuario cuando las herramientas fallan debido a argumentos incorrectos
- Falta de validación de parámetros de la herramienta antes de la ejecución
- Falta de documentación de parámetros en los prompts del agente

### Objetivos

- [ ] Permitir que las configuraciones de las herramientas MCP especifiquen los argumentos esperados (nombre, tipo, descripción)
- [ ] Actualizar el administrador de agentes para exponer los argumentos de las herramientas MCP a los LLMs a través de prompts
- [ ] Mantener la compatibilidad hacia atrás con las configuraciones existentes de las herramientas MCP
- [ ] Soporte para la validación de argumentos similar a las herramientas de plantillas de prompts

### Objetivos No
- Descubrimiento dinámico de argumentos de los servidores MCP (mejoras futuras)
- Validación de tipos de argumentos más allá de la estructura básica
- Esquemas de argumentos complejos (objetos anidados, arrays)

## Antecedentes y Contexto

### Estado Actual
Las herramientas MCP se configuran en el sistema de agente ReACT con metadatos mínimos:
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance",
  "description": "Obtener el saldo de la cuenta bancaria",
  "mcp-tool": "get_bank_balance"
}
```

El método `McpToolImpl.get_arguments()` devuelve `[]`, lo que significa que los LLMs no reciben ninguna guía de argumentos en sus prompts.

### Limitaciones

1. **Sin especificación de argumentos**: Las herramientas MCP no pueden definir parámetros esperados

2. **Inferencia de parámetros por parte del LLM**: Los agentes deben deducir parámetros a partir de los nombres/descripciones de las herramientas

3. **Falta de información en el prompt**: Los prompts de los agentes no muestran detalles de los argumentos para las herramientas MCP

4. **Sin validación**: Los parámetros inválidos solo se detectan en el momento de la ejecución de la herramienta MCP

### Componentes Relacionados
- **trustgraph-flow/agent/react/service.py**: Carga de la configuración de las herramientas y creación del AgentManager
- **trustgraph-flow/agent/react/tools.py**: Implementación de McpToolImpl
- **trustgraph-flow/agent/react/agent_manager.py**: Generación de prompts con argumentos de las herramientas
- **CLI tools**: Herramientas de línea de comandos para la gestión de herramientas MCP
- **Workbench**: Interfaz de usuario externa para la configuración de las herramientas de los agentes

## Requisitos

### Requisitos Funcionales

1. **Argumentos de la Configuración de la Herramienta MCP**: Las configuraciones de las herramientas MCP **DEBEN** soportar un array opcional de `arguments` con campos de nombre, tipo y descripción
2. **Exposición de Argumentos**: El método `McpToolImpl.get_arguments()` **DEBE** devolver los argumentos configurados en lugar de una lista vacía
3. **Integración en el Prompt**: Los prompts de los agentes **DEBEN** incluir detalles de los argumentos de las herramientas MCP cuando se especifican
4. **Compatibilidad hacia atrás**: Las configuraciones existentes de las herramientas MCP sin argumentos **DEBEN** seguir funcionando
5. **Soporte CLI**: Las herramientas CLI existentes (`tg-invoke-mcp-tool`) soportan argumentos (ya implementado)

### Requisitos No Funcionales
1. **Compatibilidad hacia atrás**: Sin cambios que rompan con las configuraciones existentes de las herramientas MCP
2. **Rendimiento**: Sin impacto significativo en el rendimiento de la generación de prompts
3. **Consistencia**: El manejo de argumentos **DEBE** seguir los patrones de las herramientas de plantillas de prompts

### Historias de Usuario

1. Como **desarrollador de agentes**, quiero especificar argumentos para las herramientas MCP en la configuración, para que los LLMs puedan invocar las herramientas con los parámetros correctos
2. Como **usuario de Workbench**, quiero configurar argumentos para las herramientas MCP en la interfaz de usuario, para que los agentes usen las herramientas correctamente
3. Como **LLM en un agente ReACT**, quiero ver las especificaciones de argumentos de las herramientas en los prompts, para poder proporcionar los parámetros correctos

## Diseño

### Arquitectura de Alto Nivel
Extender la configuración de las herramientas MCP para que coincidan con el patrón de las plantillas de prompts, agregando:
1. Un array opcional de `arguments` a las configuraciones de las herramientas MCP
2. Modificar `McpToolImpl` para aceptar y devolver los argumentos configurados
3. Actualizar la carga de la configuración de las herramientas para manejar los argumentos de las herramientas MCP
4. Asegurar que los prompts de los agentes incluyan información sobre los argumentos de las herramientas MCP

### Esquema de Configuración
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance", 
  "description": "Obtener el saldo de la cuenta bancaria",
  "mcp-tool": "get_bank_balance",
  "arguments": [
    {
      "name": "account_id",
      "type": "string", 
      "description": "Identificador de la cuenta bancaria"
    },
    {
      "name": "date",
      "type": "string",
      "description": "Fecha para la consulta de saldo (opcional, formato: YYYY-MM-DD)"
    }
  ]
}
```

### Flujo de Datos
1. **Carga de la configuración**: La configuración de la herramienta MCP con argumentos se carga por `on_tools_config()`
2. **Creación de la herramienta**: Los argumentos se parsean y se pasan a `McpToolImpl` a través del constructor
3. **Generación del prompt**: `agent_manager.py` llama a `tool.arguments` para incluirlos en los prompts de los LLMs
4. **Invocación de la herramienta**: El LLM proporciona los parámetros, que se pasan sin cambios a las herramientas MCP

## Consideraciones de Seguridad
- **Sin nueva superficie de ataque**: Los argumentos se parsean a partir de las fuentes de configuración existentes sin nuevas entradas
- **Validación de parámetros**: Los argumentos se pasan a las herramientas MCP sin cambios - la validación permanece a nivel de la herramienta MCP
- **Integridad de la configuración**: Las especificaciones de argumentos son parte de la configuración de la herramienta - el mismo modelo de seguridad aplica

## Impacto en el Rendimiento
- **Sobrehead mínimo**: El análisis de argumentos ocurre solo durante la carga de la configuración, no por solicitud
- **Aumento del tamaño del prompt**: Los prompts del agente incluirán detalles de los argumentos de las herramientas MCP, aumentando ligeramente el uso de tokens
- **Uso de la memoria**: Aumento insignificante para almacenar las especificaciones de argumentos en los objetos de la herramienta

## Documentación

### Documentación del Usuario
- [ ] Actualizar la guía de configuración de las herramientas MCP con ejemplos de argumentos
- [ ] Agregar especificación de argumentos a la ayuda de la línea de comandos
- [ ] Crear ejemplos de patrones comunes de argumentos de la herramienta MCP

### Documentación del Desarrollador
- [ ] Documentar la clase `McpToolImpl` con la lógica de análisis de argumentos
- [ ] Agregar comentarios en el código para la lógica de análisis de argumentos
- [ ] Documentar el flujo de argumentos en la arquitectura del sistema

## Preguntas Abiertas
1. **Validación de tipos**: ¿Deberíamos validar los tipos/formatos de los argumentos más allá de una verificación básica de estructura?
2. **Descubrimiento dinámico**: ¿Una futura mejora para consultar automáticamente los esquemas de las herramientas MCP de los servidores?

## Alternativas Consideradas
1. **Descubrimiento dinámico de esquemas MCP**: Consultar los servidores MCP para obtener los esquemas de las herramientas a tiempo de ejecución - rechazado debido a preocupaciones de complejidad y fiabilidad
2. **Registro de argumentos separado**: Almacenar los argumentos de las herramientas MCP en una sección de configuración separada - rechazado por mantener la consistencia con el enfoque de las plantillas de prompts
3. **Validación de tipo**: Validación completa de esquema JSON para los argumentos - aplazado como una mejora futura para mantener la implementación inicial simple

## Referencias
- [Especificación del Protocolo MCP](https://github.com/modelcontextprotocol/spec)
- [Implementación de las herramientas MCP](./trustgraph-flow/trustgraph/agent/react/service.py#L114-129)
- [Implementación actual de las herramientas MCP](./trustgraph-flow/trustgraph/agent/react/tools.py#L58-86)

## Apéndice
[Cualquier información, diagramas o ejemplos adicionales]