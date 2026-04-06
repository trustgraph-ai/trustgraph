# Especificación Técnica de la Salida JSONL para Consultas

## Resumen

Esta especificación describe la implementación del formato de salida JSONL (JSON Lines) para las respuestas de las consultas en TrustGraph. JSONL permite la extracción resistente a la truncación de datos estructurados de las respuestas de los LLM (Large Language Models), abordando problemas críticos con las salidas de matrices JSON que se corrompen cuando las respuestas de los LLM alcanzan los límites de tokens de salida.

Esta implementación admite los siguientes casos de uso:

1. **Extracción Resistente a la Truncación**: Extrae resultados parciales válidos incluso cuando la salida del LLM se trunca a la mitad de la respuesta.
2. **Extracción a Gran Escala**: Maneja la extracción de muchos elementos sin riesgo de fallo completo debido a los límites de tokens.
3. **Extracción de Tipos Mixtos**: Admite la extracción de múltiples tipos de entidades (definiciones, relaciones, entidades, atributos) en una sola consulta.
4. **Salida Compatible con Transmisión**: Permite el procesamiento futuro de transmisión/incremental de los resultados de la extracción.

## Objetivos

- **Compatibilidad Inversa**: Las consultas existentes que utilizan `response-type: "text"` y `response-type: "json"` no se ven afectadas.
- **Flexibilidad**: Permite la extracción de datos estructurados de manera más robusta y eficiente.
- **Mejora de la Experiencia del Usuario**: Proporciona resultados parciales en caso de truncamiento, mejorando la experiencia del usuario.

## Consideraciones de Diseño

- **Formato JSONL**: Cada línea de la salida representa un objeto JSON independiente.
- **Resistencia a la Truncación**: La extracción se realiza línea por línea, lo que permite recuperar datos parciales incluso si la respuesta se trunca.
- **Validación de Esquema**: Se valida cada objeto JSON contra un esquema definido para garantizar la calidad de los datos.

## Cambios en el Código

- Se introduce un nuevo tipo de respuesta: `response-type: "jsonl"`.
- Se implementa un método de análisis para procesar archivos JSONL línea por línea.
- Se modifica el método de invocación para manejar el nuevo tipo de respuesta y aplicar la validación de esquema.

## Prompts Afectados

Los siguientes prompts deben migrarse al formato JSONL:

| ID del Prompt | Descripción | Campo Tipo |
|---|---|---|
| `extract-definitions` | Extracción de entidades y definiciones | No (tipo único) |
| `extract-relationships` | Extracción de relaciones | No (tipo único) |
| `extract-topics` | Extracción de temas y definiciones | No (tipo único) |
| `extract-rows` | Extracción de filas estructuradas | No (tipo único) |
| `agent-kg-extract` | Extracción combinada de definiciones y relaciones | Sí: `"definition"`, `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | Extracción basada en ontologías | Sí: `"entity"`, `"relationship"`, `"attribute"` |

## API

No se esperan cambios en la API para los clientes. La diferencia es interna en el procesamiento de la respuesta.

## Estrategia de Pruebas

- Pruebas unitarias para validar el análisis de JSONL y la gestión de errores.
- Pruebas de integración para verificar el flujo completo de la extracción.
- Pruebas de rendimiento para evaluar el impacto en la latencia y el uso de memoria.

## Plan de Migración

1. Implementación de la lógica de análisis JSONL y la gestión del nuevo tipo de respuesta.
2. Migración de los prompts afectados al formato JSONL.
3. Actualización de cualquier código dependiente del formato de salida.

## Consideraciones de Seguridad

- El análisis JSONL utiliza las funciones estándar de `json.loads()`, lo que minimiza los riesgos de seguridad.
- La validación de esquema ayuda a garantizar la integridad de los datos.

## Preguntas Abiertas

Ninguna en este momento.

## Referencias

- Implementación actual: `trustgraph-flow/trustgraph/template/prompt_manager.py`
- Especificación JSON Lines: https://jsonlines.org/
- JSON Schema `oneOf`: https://json-schema.org/understanding-json-schema/reference/combining.html#oneof
- Especificación relacionada: Transmisión de Respuestas de LLM (`docs/tech-specs/streaming-llm-responses.md`)