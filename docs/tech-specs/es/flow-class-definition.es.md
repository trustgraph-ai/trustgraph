---
layout: default
title: "Especificación de la Definición del Esquema de Flujo"
parent: "Spanish (Beta)"
---

<<<<<<< HEAD
# Especificación de la Definición del Esquema de Flujo

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Resumen

Un esquema de flujo define una plantilla de patrón de flujo de datos completo en el sistema TrustGraph. Cuando se instancia, crea una red interconectada de procesadores que manejan la ingesta de datos, el procesamiento, el almacenamiento y la consulta como un sistema unificado.

## Estructura

Una definición de esquema de flujo consta de cinco secciones principales:

### 1. Sección de Clase
Define procesadores de servicios compartidos que se instancian una vez por esquema de flujo. Estos procesadores manejan las solicitudes de todas las instancias de flujo de esta clase.
=======
# Especificación de la Definición de la Hoja de Flujo

## Resumen

Una hoja de flujo define una plantilla de patrón de flujo de datos completo en el sistema TrustGraph. Cuando se instancia, crea una red interconectada de procesadores que manejan la ingesta de datos, el procesamiento, el almacenamiento y la consulta como un sistema unificado.

## Estructura

Una definición de hoja de flujo consta de cinco secciones principales:

### 1. Sección de Clase
Define procesadores de servicios compartidos que se instancian una vez por hoja de flujo. Estos procesadores manejan las solicitudes de todas las instancias de flujo de esta clase.
>>>>>>> 82edf2d (New md files from RunPod)

```json
"class": {
  "service-name:{class}": {
    "request": "queue-pattern:{class}",
    "response": "queue-pattern:{class}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**Características:**
Compartidas entre todas las instancias de flujo de la misma clase.
Típicamente servicios costosos o sin estado (modelos de lenguaje grandes, modelos de embedding).
Utilice la variable de plantilla `{class}` para el nombre de la cola.
Los ajustes pueden ser valores fijos o parametrizados con la sintaxis `{parameter-name}`.
Ejemplos: `embeddings:{class}`, `text-completion:{class}`, `graph-rag:{class}`.

### 2. Sección de Flujo
Define los procesadores específicos del flujo que se instancian para cada instancia de flujo individual. Cada flujo obtiene su propio conjunto aislado de estos procesadores.

```json
"flow": {
  "processor-name:{id}": {
    "input": "queue-pattern:{id}",
    "output": "queue-pattern:{id}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**Características:**
Instancia única por flujo
Maneja datos y estado específicos del flujo
Utilice la variable de plantilla `{id}` para el nombre de la cola
Los ajustes pueden ser valores fijos o parametrizados con la sintaxis `{parameter-name}`
Ejemplos: `chunker:{id}`, `pdf-decoder:{id}`, `kg-extract-relationships:{id}`

### 3. Sección de Interfaces
Define los puntos de entrada y los contratos de interacción para el flujo. Estos forman la superficie de la API para sistemas externos y comunicación entre componentes internos.

Las interfaces pueden adoptar dos formas:

**Patrón de "Enviar y Olvidar"** (cola única):
```json
"interfaces": {
  "document-load": "persistent://tg/flow/document-load:{id}",
  "triples-store": "persistent://tg/flow/triples-store:{id}"
}
```

**Patrón de solicitud/respuesta** (objeto con campos de solicitud/respuesta):
```json
"interfaces": {
  "embeddings": {
    "request": "non-persistent://tg/request/embeddings:{class}",
    "response": "non-persistent://tg/response/embeddings:{class}"
  }
}
```

**Tipos de Interfaces:**
**Puntos de Entrada**: Lugares donde los sistemas externos inyectan datos (`document-load`, `agent`)
**Interfaces de Servicio**: Patrones de solicitud/respuesta para servicios (`embeddings`, `text-completion`)
**Interfaces de Datos**: Puntos de conexión de flujo de datos "dispara y olvida" (`triples-store`, `entity-contexts-load`)

### 4. Sección de Parámetros
Mapea los nombres de parámetros específicos del flujo a definiciones de parámetros almacenadas centralmente:

```json
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "chunk": "chunk-size"
}
```

**Características:**
Las claves son nombres de parámetros utilizados en la configuración del procesador (por ejemplo, `{model}`)
Los valores hacen referencia a definiciones de parámetros almacenadas en schema/config
Permite la reutilización de definiciones de parámetros comunes en diferentes flujos
Reduce la duplicación de esquemas de parámetros

### 5. Metadatos
Información adicional sobre el plano del flujo:

```json
"description": "Human-readable description",
"tags": ["capability-1", "capability-2"]
```

## Variables de Plantilla

### Variables del Sistema

#### {id}
Reemplazado con el identificador único de la instancia del flujo.
Crea recursos aislados para cada flujo.
Ejemplo: `flow-123`, `customer-A-flow`

#### {class}
Reemplazado con el nombre de la plantilla del flujo.
Crea recursos compartidos entre flujos de la misma clase.
Ejemplo: `standard-rag`, `enterprise-rag`

### Variables de Parámetro

#### {parameter-name}
Parámetros personalizados definidos en el momento de la ejecución del flujo.
Los nombres de los parámetros coinciden con las claves en la sección `parameters` del flujo.
Se utilizan en la configuración de los procesadores para personalizar el comportamiento.
Ejemplos: `{model}`, `{temp}`, `{chunk}`
Reemplazado con los valores proporcionados al iniciar el flujo.
Validados contra definiciones de parámetros almacenadas centralmente.

## Configuración de Procesadores

La configuración proporciona valores de configuración a los procesadores en el momento de la creación. Pueden ser:

### Configuración Fija
Valores directos que no cambian:
```json
"settings": {
  "model": "gemma3:12b",
  "temperature": 0.7,
  "max_retries": 3
}
```

### Configuración parametrizada
Valores que utilizan parámetros proporcionados al iniciar el flujo:
```json
"settings": {
  "model": "{model}",
  "temperature": "{temp}",
  "endpoint": "https://{region}.api.example.com"
}
```

Los nombres de los parámetros en la configuración corresponden a las claves en la sección `parameters` del flujo.

### Ejemplos de configuración

**Procesador LLM con parámetros:**
```json
// In parameters section:
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "tokens": "max-tokens",
  "key": "openai-api-key"
}

// In processor definition:
"text-completion:{class}": {
  "request": "non-persistent://tg/request/text-completion:{class}",
  "response": "non-persistent://tg/response/text-completion:{class}",
  "settings": {
    "model": "{model}",
    "temperature": "{temp}",
    "max_tokens": "{tokens}",
    "api_key": "{key}"
  }
}
```

**Chunker con Configuraciones Fijas y Parametrizadas:**
```json
// In parameters section:
"parameters": {
  "chunk": "chunk-size"
}

// In processor definition:
"chunker:{id}": {
  "input": "persistent://tg/flow/chunk:{id}",
  "output": "persistent://tg/flow/chunk-load:{id}",
  "settings": {
    "chunk_size": "{chunk}",
    "chunk_overlap": 100,
    "encoding": "utf-8"
  }
}
```

## Patrones de Colas (Pulsar)

Los planos de flujo utilizan Apache Pulsar para el envío de mensajes. Los nombres de las colas siguen el formato de Pulsar:
```
<persistence>://<tenant>/<namespace>/<topic>
```

### Componentes:
**persistencia**: `persistent` or `non-persistent` (Modo de persistencia de Pulsar)
**inquilino**: `tg` para definiciones de planos de flujo proporcionados por TrustGraph
**espacio de nombres**: Indica el patrón de mensajería
  `flow`: Servicios de envío y olvido
  `request`: Parte de solicitud de servicios de solicitud/respuesta
  `response`: Parte de respuesta de servicios de solicitud/respuesta
**tema**: El nombre específico de la cola/tema con variables de plantilla

### Colas Persistentes
Patrón: `persistent://tg/flow/<topic>:{id}`
Utilizado para servicios de envío y olvido y flujo de datos duradero
Los datos persisten en el almacenamiento de Pulsar a través de reinicios
Ejemplo: `persistent://tg/flow/chunk-load:{id}`

### Colas No Persistentes
Patrón: `non-persistent://tg/request/<topic>:{class}` or `non-persistent://tg/response/<topic>:{class}`
Utilizado para patrones de mensajería de solicitud/respuesta
Efímero, no se persiste en disco por Pulsar
Menor latencia, adecuado para comunicación estilo RPC
Ejemplo: `non-persistent://tg/request/embeddings:{class}`

## Arquitectura del Flujo de Datos

El plano de flujo crea un flujo de datos unificado donde:

1. **Pipeline de Procesamiento de Documentos**: Fluye desde la ingesta hasta la transformación y el almacenamiento
<<<<<<< HEAD
2. **Servicios de Consulta**: Procesadores integrados que consultan las mismas bases de datos y servicios
=======
2. **Servicios de Consulta**: Procesadores integrados que consultan las mismas fuentes de datos y servicios
>>>>>>> 82edf2d (New md files from RunPod)
3. **Servicios Compartidos**: Procesadores centralizados que todos los flujos pueden utilizar
4. **Escritores de Almacenamiento**: Persisten los datos procesados en los almacenes apropiados

Todos los procesadores (tanto `{id}` como `{class}`) trabajan juntos como un gráfico de flujo de datos cohesivo, no como sistemas separados.

## Ejemplo de Instanciación de Flujo

Dado:
ID de instancia de flujo: `customer-A-flow`
Plano de flujo: `standard-rag`
Mapeos de parámetros de flujo:
  `"model": "llm-model"`
  `"temp": "temperature"`
  `"chunk": "chunk-size"`
Parámetros proporcionados por el usuario:
  `model`: `gpt-4`
  `temp`: `0.5`
  `chunk`: `512`

Expansiones de plantilla:
`persistent://tg/flow/chunk-load:{id}` → `persistent://tg/flow/chunk-load:customer-A-flow`
`non-persistent://tg/request/embeddings:{class}` → `non-persistent://tg/request/embeddings:standard-rag`
`"model": "{model}"` → `"model": "gpt-4"`
`"temperature": "{temp}"` → `"temperature": "0.5"`
`"chunk_size": "{chunk}"` → `"chunk_size": "512"`

Esto crea:
Pipeline de procesamiento de documentos aislado para `customer-A-flow`
Servicio de incrustación compartido para todos los flujos `standard-rag`
Flujo de datos completo desde la ingesta de documentos hasta la consulta
Procesadores configurados con los valores de parámetro proporcionados

## Beneficios

1. **Eficiencia de Recursos**: Los servicios costosos se comparten entre los flujos
2. **Aislamiento de Flujos**: Cada flujo tiene su propio pipeline de procesamiento de datos
3. **Escalabilidad**: Se pueden instanciar múltiples flujos desde la misma plantilla
4. **Modularidad**: Clara separación entre componentes compartidos y específicos del flujo
5. **Arquitectura Unificada**: La consulta y el procesamiento son parte del mismo flujo de datos
