---
layout: default
title: "Grupo de Herramientas TrustGraph"
parent: "Spanish (Beta)"
---

# Grupo de Herramientas TrustGraph

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.
## Especificación Técnica v1.0

### Resumen Ejecutivo

Esta especificación define un sistema de agrupación de herramientas para agentes de TrustGraph que permite un control preciso sobre qué herramientas están disponibles para solicitudes específicas. El sistema introduce un filtrado de herramientas basado en grupos a través de la configuración y la especificación a nivel de solicitud, lo que permite mejores límites de seguridad, gestión de recursos y partición funcional de las capacidades de los agentes.

### 1. Descripción General

#### 1.1 Declaración del Problema

Actualmente, los agentes de TrustGraph tienen acceso a todas las herramientas configuradas, independientemente del contexto de la solicitud o los requisitos de seguridad. Esto crea varios desafíos:

**Riesgo de Seguridad**: Herramientas sensibles (por ejemplo, modificación de datos) están disponibles incluso para consultas de solo lectura.
**Desperdicio de Recursos**: Se cargan herramientas complejas incluso cuando las consultas simples no las requieren.
**Confusión Funcional**: Los agentes pueden seleccionar herramientas inapropiadas cuando existen alternativas más simples.
**Aislamiento Multi-inquilino**: Diferentes grupos de usuarios necesitan acceso a diferentes conjuntos de herramientas.

#### 1.2 Descripción General de la Solución

El sistema de agrupación de herramientas introduce:

1. **Clasificación por Grupos**: Las herramientas se etiquetan con membresías de grupos durante la configuración.
2. **Filtrado a Nivel de Solicitud**: AgentRequest especifica qué grupos de herramientas están permitidos.
3. **Aplicación en Tiempo de Ejecución**: Los agentes solo tienen acceso a las herramientas que coinciden con los grupos solicitados.
4. **Agrupación Flexible**: Las herramientas pueden pertenecer a múltiples grupos para escenarios complejos.

### 2. Cambios en el Esquema

#### 2.1 Mejora del Esquema de Configuración de Herramientas

La configuración de herramientas existente se mejora con un campo `group`:

**Antes:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query", 
  "description": "Query the knowledge graph"
}
```

**Después:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"]
}
```

**Especificación del campo de grupo:**
`group`: Array(String) - Lista de grupos a los que pertenece esta herramienta.
**Opcional**: Las herramientas sin campo de grupo pertenecen al grupo "predeterminado".
**Múltiple pertenencia**: Las herramientas pueden pertenecer a múltiples grupos.
**Sensible a mayúsculas y minúsculas**: Los nombres de los grupos deben coincidir exactamente con la cadena.

#### 2.1.2 Mejora de la transición de estado de la herramienta

Las herramientas pueden especificar opcionalmente transiciones de estado y disponibilidad basada en el estado:

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

**Especificación del campo de estado:**
`state`: String - **Opcional** - Estado al que se debe pasar después de la ejecución exitosa de la herramienta.
`available_in_states`: Array(String) - **Opcional** - Estados en los que esta herramienta está disponible.
**Comportamiento predeterminado**: Las herramientas sin `available_in_states` están disponibles en todos los estados.
**Transición de estado**: Solo ocurre después de la ejecución exitosa de la herramienta.

#### 2.2 Mejora del esquema AgentRequest

El esquema `AgentRequest` en `trustgraph-base/trustgraph/schema/services/agent.py` se ha mejorado:

**AgentRequest actual:**
`question`: String - Consulta del usuario.
`plan`: String - Plan de ejecución (se puede eliminar).
`state`: String - Estado del agente.
`history`: Array(AgentStep) - Historial de ejecución.

**AgentRequest mejorado:**
`question`: String - Consulta del usuario.
`state`: String - Estado de ejecución del agente (ahora se utiliza activamente para el filtrado de herramientas).
`history`: Array(AgentStep) - Historial de ejecución.
`group`: Array(String) - **NUEVO** - Grupos de herramientas permitidos para esta solicitud.

**Cambios en el esquema:**
**Eliminado**: El campo `plan` ya no es necesario y se puede eliminar (originalmente estaba destinado a la especificación de herramientas).
**Añadido**: El campo `group` para la especificación de grupos de herramientas.
**Mejorado**: El campo `state` ahora controla la disponibilidad de herramientas durante la ejecución.

**Comportamientos de los campos:**

**Grupo de campos:**
**Opcional**: Si no se especifica, el valor predeterminado es ["default"].
**Intersección**: Solo las herramientas que coinciden con al menos un grupo especificado están disponibles.
**Arreglo vacío**: No hay herramientas disponibles (el agente solo puede usar el razonamiento interno).
**Comodín**: El grupo especial "*" otorga acceso a todas las herramientas.

**Campo de estado:**
**Opcional**: Si no se especifica, el valor predeterminado es "undefined".
**Filtrado basado en el estado**: Solo las herramientas disponibles en el estado actual son elegibles.
**Estado predeterminado**: El estado "undefined" permite todas las herramientas (sujeto al filtrado de grupos).
**Transiciones de estado**: Las herramientas pueden cambiar de estado después de una ejecución exitosa.

### 3. Ejemplos de grupos personalizados

Las organizaciones pueden definir grupos específicos del dominio:

```json
{
  "financial-tools": ["stock-query", "portfolio-analysis"],
  "medical-tools": ["diagnosis-assist", "drug-interaction"],
  "legal-tools": ["contract-analysis", "case-search"]
}
```

### 4. Detalles de implementación

#### 4.1 Carga y filtrado de herramientas

**Fase de configuración:**
1. Todas las herramientas se cargan desde la configuración con sus asignaciones de grupo.
2. Las herramientas sin grupos explícitos se asignan al grupo "predeterminado".
3. La pertenencia al grupo se valida y se almacena en el registro de herramientas.

**Fase de procesamiento de solicitudes:**
1. La solicitud del agente llega con una especificación de grupo opcional.
2. El agente filtra las herramientas disponibles según la intersección de grupos.
3. Solo las herramientas que coinciden se pasan al contexto de ejecución del agente.
4. El agente opera con el conjunto de herramientas filtrado durante todo el ciclo de vida de la solicitud.

#### 4.2 Lógica de filtrado de herramientas

**Filtrado combinado de grupos y estado:**

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

**Lógica de transición de estado:**

```
After successful tool execution:
  if tool.state is defined:
    next_request.state = tool.state
  else:
    next_request.state = current_request.state  // No change
```

#### 4.3 Puntos de Integración del Agente

**Agente ReAct:**
El filtrado de herramientas se produce en agent_manager.py durante la creación del registro de herramientas.
La lista de herramientas disponibles se filtra tanto por grupo como por estado antes de la generación del plan.
Las transiciones de estado actualizan el campo AgentRequest.state después de la ejecución exitosa de la herramienta.
La siguiente iteración utiliza el estado actualizado para el filtrado de herramientas.

**Agente Basado en la Confianza:**
El filtrado de herramientas se produce en planner.py durante la generación del plan.
La validación de ExecutionStep asegura que solo se utilicen las herramientas elegibles por grupo y estado.
El controlador de flujo hace cumplir la disponibilidad de las herramientas en tiempo de ejecución.
Las transiciones de estado son gestionadas por el Controlador de Flujo entre los pasos.

### 5. Ejemplos de Configuración

#### 5.1 Configuración de Herramientas con Grupos y Estados

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

#### 5.2 Ejemplos de solicitudes con flujos de trabajo de estado

**Solicitud de investigación inicial:**
```json
{
  "question": "What entities are connected to Company X?",
  "group": ["read-only", "knowledge"],
  "state": "undefined"
}
```
*Herramientas disponibles: knowledge-query, text-completion*
*Después de knowledge-query: estado → "análisis"*

**Fase de análisis:**
```json
{
  "question": "Continue analysis based on previous results",
  "group": ["advanced", "compute", "write"],
  "state": "analysis"
}
```
*Herramientas disponibles: análisis complejo, actualización de gráficos, restablecimiento del flujo de trabajo*
*Después del análisis complejo: estado → "resultados"*

**Fase de resultados:**
```json
{
  "question": "What should I do with these results?",
  "group": ["admin"],
  "state": "results"
}
```
*Herramientas disponibles: reset-workflow solamente*
*Después de reset-workflow: estado → "indefinido"*

**Ejemplo de flujo de trabajo: flujo completo:**
1. **Inicio (indefinido):** Use knowledge-query → transiciones a "análisis"
2. **Estado de análisis:** Use complex-analysis → transiciones a "resultados"
3. **Estado de resultados:** Use reset-workflow → transiciones de vuelta a "indefinido"
4. **De vuelta al inicio:** Todas las herramientas iniciales están disponibles nuevamente

### 6. Consideraciones de seguridad

#### 6.1 Integración de control de acceso

**Filtrado a nivel de puerta de enlace:**
La puerta de enlace puede hacer cumplir las restricciones de grupo basadas en los permisos del usuario
Prevenir la elevación de privilegios a través de la manipulación de solicitudes
El registro de auditoría incluye los grupos de herramientas solicitados y concedidos

**Ejemplo de lógica de la puerta de enlace:**
```
user_permissions = get_user_permissions(request.user_id)
allowed_groups = user_permissions.tool_groups
requested_groups = request.group

# Validate request doesn't exceed permissions
if not is_subset(requested_groups, allowed_groups):
    reject_request("Insufficient permissions for requested tool groups")
```

#### 6.2 Auditoría y Monitoreo

**Registro de Auditoría Mejorado:**
Registrar los grupos de herramientas solicitados y el estado inicial por solicitud.
Registrar las transiciones de estado y el uso de herramientas por pertenencia a un grupo.
Monitorear los intentos de acceso no autorizados a grupos y las transiciones de estado inválidas.
Generar alertas sobre patrones de uso de grupos inusuales o flujos de trabajo de estado sospechosos.

### 7. Estrategia de Migración

#### 7.1 Compatibilidad con Versiones Anteriores

**Fase 1: Cambios Aditivos**
Agregar un campo opcional `group` a las configuraciones de las herramientas.
Agregar un campo opcional `group` al esquema de AgentRequest.
Comportamiento predeterminado: Todas las herramientas existentes pertenecen al grupo "predeterminado".
Las solicitudes existentes sin el campo de grupo utilizan el grupo "predeterminado".

**Comportamiento Existente Preservado:**
Las herramientas sin configuración de grupo siguen funcionando (grupo predeterminado).
Las herramientas sin configuración de estado están disponibles en todos los estados.
Las solicitudes sin especificación de grupo acceden a todas las herramientas (grupo predeterminado).
Las solicitudes sin especificación de estado utilizan el estado "indefinido" (todas las herramientas disponibles).
No hay cambios que rompan la compatibilidad con las implementaciones existentes.

### 8. Monitoreo y Observabilidad

#### 8.1 Nuevas Métricas

**Uso de Grupos de Herramientas:**
`agent_tool_group_requests_total` - Contador de solicitudes por grupo.
`agent_tool_group_availability` - Indicador de herramientas disponibles por grupo.
`agent_filtered_tools_count` - Histograma del número de herramientas después del filtrado por grupo + estado.

**Métricas de Flujo de Trabajo de Estado:**
`agent_state_transitions_total` - Contador de transiciones de estado por herramienta.
`agent_workflow_duration_seconds` - Histograma del tiempo empleado en cada estado.
`agent_state_availability` - Indicador de herramientas disponibles por estado.

**Métricas de Seguridad:**
`agent_group_access_denied_total` - Contador de accesos no autorizados a grupos.
`agent_invalid_state_transition_total` - Contador de transiciones de estado inválidas.
`agent_privilege_escalation_attempts_total` - Contador de solicitudes sospechosas.

#### 8.2 Mejoras en el Registro

**Registro de Solicitudes:**
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

### 9. Estrategia de Pruebas

#### 9.1 Pruebas Unitarias

**Lógica de Filtrado de Herramientas:**
Cálculos de intersección de grupos de pruebas
Lógica de filtrado basada en el estado de la prueba
Verificar la asignación predeterminada de grupos y estados
Probar el comportamiento de los comodines en los grupos
Validar el manejo de grupos vacíos
Probar escenarios de filtrado combinados de grupos y estados

**Validación de la Configuración:**
Probar la carga de herramientas con varias configuraciones de grupos y estados
Verificar la validación del esquema para especificaciones inválidas de grupos y estados
Probar la compatibilidad con versiones anteriores con las configuraciones existentes
Validar las definiciones y ciclos de transición de estados

#### 9.2 Pruebas de Integración

**Comportamiento del Agente:**
Verificar que los agentes solo vean las herramientas filtradas por grupo y estado
Probar la ejecución de solicitudes con varias combinaciones de grupos
Probar las transiciones de estado durante la ejecución del agente
Validar el manejo de errores cuando no hay herramientas disponibles
Probar el progreso del flujo de trabajo a través de múltiples estados

**Pruebas de Seguridad:**
Probar la prevención de la escalada de privilegios
Verificar la precisión del registro de auditoría
Probar la integración de la puerta de enlace con los permisos de usuario

#### 9.3 Escenarios de Extremo a Extremo

**Uso Multi-inquilino con Flujos de Trabajo de Estado:**
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

**Progresión del estado del flujo de trabajo:**
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

### 10. Consideraciones de rendimiento

#### 10.1 Impacto de la carga de herramientas

**Carga de configuración:**
Los metadatos del grupo y el estado se cargan una vez al inicio.
Sobrecarga de memoria mínima por herramienta (campos adicionales).
No hay impacto en el tiempo de inicialización de la herramienta.

**Procesamiento de solicitudes:**
El filtrado combinado de grupo+estado se realiza una vez por solicitud.
Complejidad O(n), donde n = número de herramientas configuradas.
Las transiciones de estado agregan una sobrecarga mínima (asignación de cadenas).
Impacto insignificante para un número típico de herramientas (< 100).

#### 10.2 Estrategias de optimización

**Conjuntos de herramientas precalculados:**
Almacenar en caché los conjuntos de herramientas por combinación de grupo+estado.
Evitar el filtrado repetido para patrones comunes de grupo/estado.
Intercambio entre memoria y computación para combinaciones de uso frecuente.

**Carga diferida:**
Cargar las implementaciones de las herramientas solo cuando sea necesario.
Reducir el tiempo de inicio para implementaciones con muchas herramientas.
Registro dinámico de herramientas basado en los requisitos del grupo.

### 11. Mejoras futuras

#### 11.1 Asignación dinámica de grupos

**Agrupación con conocimiento del contexto:**
Asignar herramientas a grupos según el contexto de la solicitud.
Disponibilidad del grupo basada en el tiempo (solo durante el horario de atención).
Restricciones de grupo basadas en la carga (herramientas costosas durante el bajo uso).

#### 11.2 Jerarquías de grupos

**Estructura de grupo anidada:**
```json
{
  "knowledge": {
    "read": ["knowledge-query", "entity-search"],
    "write": ["graph-update", "entity-create"]
  }
}
```

#### 11.3 Recomendaciones de herramientas

**Sugerencias basadas en grupos:**
Sugerir grupos de herramientas óptimos para tipos de solicitud.
Aprender de los patrones de uso para mejorar las recomendaciones.
Proporcionar grupos de respaldo cuando las herramientas preferidas no están disponibles.

### 12. Preguntas abiertas

1. **Validación de grupos**: ¿Deben los nombres de grupo no válidos en las solicitudes causar errores graves o advertencias?

2. **Descubrimiento de grupos**: ¿Debería el sistema proporcionar una API para listar los grupos disponibles y sus herramientas?

3. **Grupos dinámicos**: ¿Deben los grupos ser configurables en tiempo de ejecución o solo al inicio?

4. **Herencia de grupos**: ¿Deben las herramientas heredar grupos de sus categorías o implementaciones principales?

5. **Monitoreo del rendimiento**: ¿Qué métricas adicionales son necesarias para realizar un seguimiento eficaz del uso de herramientas basado en grupos?

### 13. Conclusión

El sistema de grupos de herramientas proporciona:

**Seguridad**: Control de acceso granular sobre las capacidades del agente.
**Rendimiento**: Reducción de la sobrecarga de carga y selección de herramientas.
**Flexibilidad**: Clasificación de herramientas multidimensional.
**Compatibilidad**: Integración perfecta con arquitecturas de agentes existentes.

Este sistema permite que las implementaciones de TrustGraph gestionen mejor el acceso a las herramientas, mejoren los límites de seguridad y optimicen el uso de recursos, al tiempo que mantiene la compatibilidad con versiones anteriores con las configuraciones y solicitudes existentes.
