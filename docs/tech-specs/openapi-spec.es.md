# Especificación OpenAPI - Especificación Técnica

## Objetivo

Crear una especificación OpenAPI 3.1 completa y modular para la puerta de enlace de la API REST de TrustGraph que:
Documente todos los puntos finales REST.
Utilice `$ref` externo para la modularidad y el mantenimiento.
Se mapee directamente con el código del traductor de mensajes.
Proporcione esquemas precisos de solicitud/respuesta.

## Fuente de la Verdad

La API está definida por:
**Traductores de Mensajes**: `trustgraph-base/trustgraph/messaging/translators/*.py`
**Administrador del Despachador**: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
**Administrador de Puntos Finales**: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`

## Estructura de Directorios

```
openapi/
├── openapi.yaml                          # Main entry point
├── paths/
│   ├── config.yaml                       # Global services
│   ├── flow.yaml
│   ├── librarian.yaml
│   ├── knowledge.yaml
│   ├── collection-management.yaml
│   ├── flow-services/                    # Flow-hosted services
│   │   ├── agent.yaml
│   │   ├── document-rag.yaml
│   │   ├── graph-rag.yaml
│   │   ├── text-completion.yaml
│   │   ├── prompt.yaml
│   │   ├── embeddings.yaml
│   │   ├── mcp-tool.yaml
│   │   ├── triples.yaml
│   │   ├── objects.yaml
│   │   ├── nlp-query.yaml
│   │   ├── structured-query.yaml
│   │   ├── structured-diag.yaml
│   │   ├── graph-embeddings.yaml
│   │   ├── document-embeddings.yaml
│   │   ├── text-load.yaml
│   │   └── document-load.yaml
│   ├── import-export/
│   │   ├── core-import.yaml
│   │   ├── core-export.yaml
│   │   └── flow-import-export.yaml      # WebSocket import/export
│   ├── websocket.yaml
│   └── metrics.yaml
├── components/
│   ├── schemas/
│   │   ├── config/
│   │   ├── flow/
│   │   ├── librarian/
│   │   ├── knowledge/
│   │   ├── collection/
│   │   ├── ai-services/
│   │   ├── common/
│   │   └── errors/
│   ├── parameters/
│   ├── responses/
│   └── examples/
└── security/
    └── bearerAuth.yaml
```

## Mapeo de Servicios

### Servicios Globales (`/api/v1/{kind}`)
`config` - Gestión de configuración
`flow` - Ciclo de vida del flujo
`librarian` - Biblioteca de documentos
`knowledge` - Núcleos de conocimiento
`collection-management` - Metadatos de colección

### Servicios Alojados en el Flujo (`/api/v1/flow/{flow}/service/{kind}`)

**Solicitud/Respuesta:**
`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `objects`, `nlp-query`, `structured-query`, `structured-diag`

**Enviar y Olvidar:**
`text-load`, `document-load`

### Importación/Exportación
`/api/v1/import-core` (POST)
`/api/v1/export-core` (GET)
`/api/v1/flow/{flow}/import/{kind}` (WebSocket)
`/api/v1/flow/{flow}/export/{kind}` (WebSocket)

### Otros
`/api/v1/socket` (WebSocket multiplexado)
`/api/metrics` (Prometheus)

## Enfoque

### Fase 1: Configuración
1. Crear estructura de directorios
2. Crear el archivo principal `openapi.yaml` con metadatos, servidores, seguridad
3. Crear componentes reutilizables (errores, parámetros comunes, esquemas de seguridad)

### Fase 2: Esquemas Comunes
Crear esquemas compartidos utilizados en todos los servicios:
`RdfValue`, `Triple` - Estructuras RDF/triple
`ErrorObject` - Respuesta de error
`DocumentMetadata`, `ProcessingMetadata` - Estructuras de metadatos
Parámetros comunes: `FlowId`, `User`, `Collection`

### Fase 3: Servicios Globales
Para cada servicio global (configuración, flujo, biblioteca, conocimiento, gestión de colecciones):
1. Crear el archivo de ruta en `paths/`
2. Crear el esquema de solicitud en `components/schemas/{service}/`
3. Crear el esquema de respuesta
4. Agregar ejemplos
5. Referenciar desde el archivo principal `openapi.yaml`

### Fase 4: Servicios Alojados en el Flujo
Para cada servicio alojado en el flujo:
1. Crear el archivo de ruta en `paths/flow-services/`
2. Crear los esquemas de solicitud/respuesta en `components/schemas/ai-services/`
3. Agregar la documentación de la bandera de transmisión cuando corresponda
4. Referenciar desde el archivo principal `openapi.yaml`

### Fase 5: Importación/Exportación y WebSocket
1. Documentar los puntos finales principales de importación/exportación
2. Documentar los patrones de protocolo WebSocket
3. Documentar los puntos finales de importación/exportación WebSocket a nivel de flujo

### Fase 6: Validación
1. Validar con herramientas de validación de OpenAPI
2. Probar con Swagger UI
3. Verificar que todos los traductores estén cubiertos

## Convención de Nombres de Campos

Todos los campos JSON utilizan **kebab-case**:
`flow-id`, `blueprint-name`, `doc-limit`, `entity-limit`, etc.

## Creación de Archivos de Esquema

Para cada traductor en `trustgraph-base/trustgraph/messaging/translators/`:

1. **Leer el método del traductor `to_pulsar()`** - Define el esquema de solicitud
2. **Leer el método del traductor `from_pulsar()`** - Define el esquema de respuesta
3. **Extraer nombres y tipos de campos**
4. **Crear el esquema OpenAPI** con:
   Nombres de campos (kebab-case)
   Tipos (string, integer, boolean, object, array)
   Campos obligatorios
   Valores predeterminados
   Descripciones

### Ejemplo de Proceso de Mapeo

```python
# From retrieval.py DocumentRagRequestTranslator
def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagQuery:
    return DocumentRagQuery(
        query=data["query"],                              # required string
        user=data.get("user", "trustgraph"),             # optional string, default "trustgraph"
        collection=data.get("collection", "default"),     # optional string, default "default"
        doc_limit=int(data.get("doc-limit", 20)),        # optional integer, default 20
        streaming=data.get("streaming", False)            # optional boolean, default false
    )
```

Traducción:

```yaml
# components/schemas/ai-services/DocumentRagRequest.yaml
type: object
required:
  - query
properties:
  query:
    type: string
    description: Search query
  user:
    type: string
    default: trustgraph
  collection:
    type: string
    default: default
  doc-limit:
    type: integer
    default: 20
    description: Maximum number of documents to retrieve
  streaming:
    type: boolean
    default: false
    description: Enable streaming responses
```

## Respuestas de transmisión

Los servicios que admiten la transmisión devuelven múltiples respuestas con la bandera `end_of_stream`:
`agent`, `text-completion`, `prompt`
`document-rag`, `graph-rag`

Documente este patrón en el esquema de respuesta de cada servicio.

## Respuestas de error

Todos los servicios pueden devolver:
```yaml
error:
  oneOf:
    - type: string
    - $ref: '#/components/schemas/ErrorObject'
```

Donde `ErrorObject` es:
```yaml
type: object
properties:
  type:
    type: string
  message:
    type: string
```

## Referencias

Traductores: `trustgraph-base/trustgraph/messaging/translators/`
Mapeo del despachador: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
Enrutamiento de puntos finales: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`
Resumen del servicio: `API_SERVICES_SUMMARY.md`
