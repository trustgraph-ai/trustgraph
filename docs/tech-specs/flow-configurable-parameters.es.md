---
layout: default
title: "Especificación Técnica de Parámetros Configurables para Flow Blueprint"
parent: "Spanish (Beta)"
---

<<<<<<< HEAD
# Especificación Técnica de Parámetros Configurables para Flow Blueprint

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Resumen

Esta especificación describe la implementación de parámetros configurables para flow blueprints en TrustGraph. Los parámetros permiten a los usuarios personalizar los parámetros del procesador en el momento de la ejecución del flujo, proporcionando valores que reemplazan los marcadores de posición de parámetros en la definición del flow blueprint.

Los parámetros funcionan a través de la sustitución de variables de plantilla en los parámetros del procesador, de manera similar a cómo funcionan las variables `{id}` y `{class}`, pero con valores proporcionados por el usuario.

La integración admite cuatro casos de uso principales:

1. **Selección de Modelo**: Permitir a los usuarios elegir diferentes modelos LLM (por ejemplo, `gemma3:8b`, `gpt-4`, `claude-3`) para los procesadores.
2. **Configuración de Recursos**: Ajustar los parámetros del procesador, como los tamaños de lote, los tamaños de lote y los límites de concurrencia.
=======
# Especificación Técnica de Parámetros Configurables para el Blueprint de Flujo

## Resumen

Esta especificación describe la implementación de parámetros configurables para blueprints de flujo en TrustGraph. Los parámetros permiten a los usuarios personalizar los parámetros del procesador en el momento de la ejecución del flujo, proporcionando valores que reemplazan los marcadores de posición de parámetros en la definición del blueprint del flujo.

Los parámetros funcionan mediante la sustitución de variables de plantilla en los parámetros del procesador, de manera similar a como funcionan las variables `{id}` y `{class}`, pero con valores proporcionados por el usuario.

La integración admite cuatro casos de uso principales:

1. **Selección de Modelo**: Permitir a los usuarios elegir diferentes modelos de LLM (por ejemplo, `gemma3:8b`, `gpt-4`, `claude-3`) para los procesadores.
2. **Configuración de Recursos**: Ajustar los parámetros del procesador, como los tamaños de lote, los tamaños de fragmento y los límites de concurrencia.
>>>>>>> 82edf2d (New md files from RunPod)
3. **Ajuste del Comportamiento**: Modificar el comportamiento del procesador a través de parámetros como la temperatura, el número máximo de tokens o los umbrales de recuperación.
4. **Parámetros Específicos del Entorno**: Configurar puntos finales, claves de API o URL específicas de la región para cada implementación.

## Objetivos

<<<<<<< HEAD
**Configuración Dinámica del Procesador**: Permitir la configuración en tiempo de ejecución de los parámetros del procesador a través de la sustitución de parámetros.
**Validación de Parámetros**: Proporcionar verificación de tipos y validación para los parámetros en el momento de la ejecución del flujo.
**Valores Predeterminados**: Admitir valores predeterminados sensatos, al tiempo que se permite la sobrescritura para usuarios avanzados.
**Sustitución de Plantillas**: Reemplazar sin problemas los marcadores de posición de parámetros en los parámetros del procesador.
**Integración de la Interfaz de Usuario**: Permitir la entrada de parámetros a través de interfaces de API y de interfaz de usuario.
**Seguridad de Tipos**: Asegurar que los tipos de parámetros coincidan con los tipos de parámetros del procesador esperados.
**Documentación**: Esquemas de parámetros auto-documentados dentro de las definiciones de flow blueprint.
**Compatibilidad con Versiones Anteriores**: Mantener la compatibilidad con los flow blueprints existentes que no utilizan parámetros.

## Antecedentes

Los flow blueprints en TrustGraph ahora admiten parámetros de procesador que pueden contener valores fijos o marcadores de posición de parámetros. Esto crea una oportunidad para la personalización en tiempo de ejecución.
=======
**Configuración Dinámica del Procesador**: Permitir la configuración en tiempo de ejecución de los parámetros del procesador mediante la sustitución de parámetros.
**Validación de Parámetros**: Proporcionar verificación de tipos y validación para los parámetros en el momento de la ejecución del flujo.
**Valores Predeterminados**: Admitir valores predeterminados razonables, al tiempo que se permite la sobrescritura para usuarios avanzados.
**Sustitución de Plantillas**: Reemplazar sin problemas los marcadores de posición de parámetros en los parámetros del procesador.
**Integración de la Interfaz de Usuario**: Permitir la entrada de parámetros a través de interfaces de API y de la interfaz de usuario.
**Seguridad de Tipos**: Asegurar que los tipos de parámetros coincidan con los tipos de parámetros del procesador esperados.
**Documentación**: Esquemas de parámetros auto-documentados dentro de las definiciones de blueprints de flujo.
**Compatibilidad con Versiones Anteriores**: Mantener la compatibilidad con los blueprints de flujo existentes que no utilizan parámetros.

## Antecedentes

Los blueprints de flujo en TrustGraph ahora admiten parámetros de procesador que pueden contener valores fijos o marcadores de posición de parámetros. Esto crea una oportunidad para la personalización en tiempo de ejecución.
>>>>>>> 82edf2d (New md files from RunPod)

Los parámetros de procesador actuales admiten:
Valores fijos: `"model": "gemma3:12b"`
Marcadores de posición de parámetros: `"model": "gemma3:{model-size}"`

Esta especificación define cómo se:
<<<<<<< HEAD
Declaran en las definiciones de flow blueprint.
=======
Declaran en las definiciones de blueprints de flujo.
>>>>>>> 82edf2d (New md files from RunPod)
Validan cuando se ejecutan los flujos.
Sustituyen en los parámetros del procesador.
Exponen a través de las API y la interfaz de usuario.

Al aprovechar los parámetros de procesador parametrizados, TrustGraph puede:
<<<<<<< HEAD
Reducir la duplicación de flow blueprints mediante el uso de parámetros para las variaciones.
=======
Reducir la duplicación de blueprints de flujo mediante el uso de parámetros para las variaciones.
>>>>>>> 82edf2d (New md files from RunPod)
Permitir a los usuarios ajustar el comportamiento del procesador sin modificar las definiciones.
Admitir configuraciones específicas del entorno a través de los valores de los parámetros.
Mantener la seguridad de tipos a través de la validación del esquema de parámetros.

## Diseño Técnico

### Arquitectura

El sistema de parámetros configurables requiere los siguientes componentes técnicos:

1. **Definición del Esquema de Parámetros**
<<<<<<< HEAD
   Definiciones de parámetros basadas en JSON Schema dentro de los metadatos del flow blueprint.
=======
   Definiciones de parámetros basadas en esquemas JSON dentro de los metadatos del blueprint de flujo.
>>>>>>> 82edf2d (New md files from RunPod)
   Definiciones de tipos que incluyen cadenas, números, booleanos, enumeraciones y tipos de objetos.
   Reglas de validación que incluyen valores mínimos/máximos, patrones y campos obligatorios.

   Módulo: trustgraph-flow/trustgraph/flow/definition.py

2. **Motor de Resolución de Parámetros**
   Validación de parámetros en tiempo de ejecución contra el esquema.
   Aplicación de valores predeterminados para los parámetros no especificados.
   Inyección de parámetros en el contexto de ejecución del flujo.
   Coerción y conversión de tipos según sea necesario.

   Módulo: trustgraph-flow/trustgraph/flow/parameter_resolver.py

3. **Integración del Almacén de Parámetros**
   Recuperación de definiciones de parámetros del almacén de esquemas/configuración.
   Almacenamiento en caché de definiciones de parámetros utilizadas con frecuencia.
   Validación contra esquemas almacenados centralmente.

   Módulo: trustgraph-flow/trustgraph/flow/parameter_store.py

4. **Extensiones del Lanzador de Flujos**
   Extensiones de API para aceptar valores de parámetros durante el lanzamiento del flujo.
   Resolución de mapeo de parámetros (nombres de flujo a nombres de definición).
   Manejo de errores para combinaciones de parámetros no válidas.

   Módulo: trustgraph-flow/trustgraph/flow/launcher.py

5. **Formularios de Parámetros de la Interfaz de Usuario**
<<<<<<< HEAD
   Generación dinámica de formularios a partir de los metadatos de los parámetros del flujo.
   Visualización ordenada de parámetros utilizando el campo `order`.
   Etiquetas descriptivas de parámetros utilizando el campo `description`.
   Validación de entrada contra las definiciones de tipo de parámetro.
=======
   Generación dinámica de formularios a partir de metadatos de parámetros del flujo.
   Visualización ordenada de parámetros utilizando el campo `order`.
   Etiquetas descriptivas de parámetros utilizando el campo `description`.
   Validación de entrada contra definiciones de tipos de parámetros.
>>>>>>> 82edf2d (New md files from RunPod)
   Preajustes y plantillas de parámetros.

   Módulo: trustgraph-ui/components/flow-parameters/

### Modelos de Datos

#### Definiciones de Parámetros (Almacenadas en Esquema/Configuración)

Las definiciones de parámetros se almacenan centralmente en el sistema de esquemas y configuración con el tipo "parameter-type":

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

#### Diagrama de flujo con referencias de parámetros

Los diagramas de flujo definen los metadatos de los parámetros con referencias de tipo, descripciones y orden:

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

<<<<<<< HEAD
La sección `parameters` mapea los nombres de parámetros específicos del flujo (claves) a objetos de metadatos de parámetros que contienen:
`type`: Referencia a la definición de parámetro definida centralmente (por ejemplo, "llm-model")
`description`: Descripción legible por humanos para su visualización en la interfaz de usuario
`order`: Orden de visualización para los formularios de parámetros (los números más bajos aparecen primero)
`advanced` (opcional): Bandera booleana que indica si este es un parámetro avanzado (por defecto: falso). Cuando se establece en verdadero, la interfaz de usuario puede ocultar este parámetro de forma predeterminada o colocarlo en una sección "Avanzado"
`controlled-by` (opcional): Nombre de otro parámetro que controla el valor de este parámetro cuando está en modo simple. Cuando se especifica, este parámetro hereda su valor del parámetro de control, a menos que se anule explícitamente

Este enfoque permite:
Definiciones de tipos de parámetros reutilizables en múltiples plantillas de flujo
Gestión y validación centralizadas de tipos de parámetros
Descripciones y orden de parámetros específicos del flujo
Experiencia de interfaz de usuario mejorada con formularios de parámetros descriptivos
Validación de parámetros consistente en todos los flujos
Adición fácil de nuevos tipos de parámetros estándar
Interfaz de usuario simplificada con separación de modo básico/avanzado
Herencia de valores de parámetros para configuraciones relacionadas

#### Solicitud de inicio de flujo

La API de inicio de flujo acepta parámetros utilizando los nombres de parámetros del flujo:
=======
La sección `parameters` asigna nombres de parámetros específicos del flujo (claves) a objetos de metadatos de parámetros que contienen:
`type`: Referencia a la definición de parámetro definida centralmente (por ejemplo, "llm-model").
`description`: Descripción legible por humanos para su visualización en la interfaz de usuario.
`order`: Orden de visualización para los formularios de parámetros (los números más bajos aparecen primero).
`advanced` (opcional): Marcador booleano que indica si este es un parámetro avanzado (por defecto: falso). Cuando se establece en verdadero, la interfaz de usuario puede ocultar este parámetro de forma predeterminada o colocarlo en una sección "Avanzado".
`controlled-by` (opcional): Nombre de otro parámetro que controla el valor de este parámetro cuando está en modo simple. Cuando se especifica, este parámetro hereda su valor del parámetro de control, a menos que se anule explícitamente.

Este enfoque permite:
Definiciones de tipos de parámetros reutilizables en múltiples plantillas de flujo.
Gestión y validación centralizadas de tipos de parámetros.
Descripciones y orden de parámetros específicos del flujo.
Experiencia de interfaz de usuario mejorada con formularios de parámetros descriptivos.
Validación de parámetros coherente en todos los flujos.
Adición fácil de nuevos tipos de parámetros estándar.
Interfaz de usuario simplificada con separación de modo básico/avanzado.
Herencia de valores de parámetros para configuraciones relacionadas.

#### Solicitud de inicio del flujo

La API de inicio del flujo acepta parámetros utilizando los nombres de parámetros del flujo:
>>>>>>> 82edf2d (New md files from RunPod)

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

Nota: En este ejemplo, `llm-rag-model` no se proporciona explícitamente, pero heredará el valor "claude-3" de `llm-model` debido a su relación `controlled-by`. De manera similar, `chunk-overlap` podría heredar un valor calculado basado en `chunk-size`.

<<<<<<< HEAD
El sistema realizará lo siguiente:
1. Extraer metadatos de parámetros de la definición de la plantilla de flujo.
=======
El sistema realizará las siguientes acciones:
1. Extraer metadatos de parámetros de la definición de la plantilla del flujo.
>>>>>>> 82edf2d (New md files from RunPod)
2. Mapear los nombres de los parámetros del flujo a sus definiciones de tipo (por ejemplo, `llm-model` → tipo `llm-model`).
3. Resolver las relaciones de control (por ejemplo, `llm-rag-model` hereda de `llm-model`).
4. Validar los valores proporcionados por el usuario y los valores heredados en función de las definiciones de tipo de los parámetros.
5. Sustituir los valores resueltos en los parámetros del procesador durante la instanciación del flujo.

### Detalles de implementación

#### Proceso de resolución de parámetros

Cuando se inicia un flujo, el sistema realiza los siguientes pasos de resolución de parámetros:

1. **Carga de la plantilla del flujo**: Cargar la definición de la plantilla del flujo y extraer los metadatos de los parámetros.
2. **Extracción de metadatos**: Extraer `type`, `description`, `order`, `advanced` y `controlled-by` para cada parámetro definido en la sección `parameters` de la plantilla del flujo.
3. **Búsqueda de la definición de tipo**: Para cada parámetro en la plantilla del flujo:
<<<<<<< HEAD
   Recuperar la definición de tipo del parámetro del almacén de esquema/configuración utilizando el campo `type`.
=======
   Recuperar la definición de tipo del parámetro del almacén de esquemas/configuración utilizando el campo `type`.
>>>>>>> 82edf2d (New md files from RunPod)
   Las definiciones de tipo se almacenan con el tipo "parameter-type" en el sistema de configuración.
   Cada definición de tipo contiene el esquema del parámetro, el valor predeterminado y las reglas de validación.
4. **Resolución del valor predeterminado**:
   Para cada parámetro definido en la plantilla del flujo:
     Comprobar si el usuario ha proporcionado un valor para este parámetro.
     Si no se proporciona ningún valor del usuario, utilizar el valor `default` de la definición de tipo del parámetro.
     Crear un mapa de parámetros completo que contenga tanto los valores proporcionados por el usuario como los valores predeterminados.
5. **Resolución de la herencia de parámetros** (relaciones de control):
   Para los parámetros con el campo `controlled-by`, comprobar si se ha proporcionado un valor explícito.
   Si no se proporciona ningún valor explícito, heredar el valor del parámetro de control.
   Si el parámetro de control también no tiene valor, utilizar el valor predeterminado de la definición de tipo.
   Validar que no existan dependencias circulares en las relaciones `controlled-by`.
6. **Validación**: Validar el conjunto completo de parámetros (proporcionados por el usuario, predeterminados y heredados) en función de las definiciones de tipo.
7. **Almacenamiento**: Almacenar el conjunto completo de parámetros resueltos con la instancia del flujo para su trazabilidad.
8. **Sustitución de plantillas**: Reemplazar los marcadores de posición de parámetros en los parámetros del procesador con los valores resueltos.
9. **Instanciación del procesador**: Crear procesadores con los parámetros sustituidos.

**Notas importantes de implementación**:
El servicio de flujo DEBE combinar los parámetros proporcionados por el usuario con los valores predeterminados de las definiciones de tipo de parámetros.
El conjunto completo de parámetros (incluidos los valores predeterminados aplicados) DEBE almacenarse con el flujo para su trazabilidad.
La resolución de parámetros se realiza al inicio del flujo, no en el momento de la instanciación del procesador.
Los parámetros obligatorios sin valores predeterminados DEBEN provocar que el inicio del flujo falle con un mensaje de error claro.

<<<<<<< HEAD
#### Herencia de parámetros con control
=======
#### Herencia de parámetros con "controlled-by"
>>>>>>> 82edf2d (New md files from RunPod)

El campo `controlled-by` permite la herencia de valores de parámetros, lo que es especialmente útil para simplificar las interfaces de usuario al tiempo que se mantiene la flexibilidad:

**Escenario de ejemplo**:
El parámetro `llm-model` controla el modelo LLM primario.
El parámetro `llm-rag-model` tiene el valor `"controlled-by": "llm-model"`.
En el modo simple, establecer `llm-model` en "gpt-4" establece automáticamente `llm-rag-model` en "gpt-4" también.
En el modo avanzado, los usuarios pueden anular `llm-rag-model` con un valor diferente.

**Reglas de resolución**:
1. Si un parámetro tiene un valor proporcionado explícitamente, utilizar ese valor.
2. Si no hay ningún valor explícito y `controlled-by` está establecido, utilizar el valor del parámetro de control.
3. Si el parámetro de control no tiene valor, recurrir al valor predeterminado de la definición de tipo.
4. Las dependencias circulares en las relaciones `controlled-by` dan como resultado un error de validación.

**Comportamiento de la interfaz de usuario**:
En el modo básico/simple: Los parámetros con `controlled-by` pueden estar ocultos o mostrarse como de solo lectura con el valor heredado.
En el modo avanzado: Se muestran todos los parámetros y se pueden configurar individualmente.
Cuando cambia un parámetro de control, los parámetros dependientes se actualizan automáticamente, a menos que se anulen explícitamente.

<<<<<<< HEAD
#### Integración de Pulsar
=======
#### Integración con Pulsar
>>>>>>> 82edf2d (New md files from RunPod)

1. **Operación de inicio de flujo**
   La operación de inicio de flujo de Pulsar debe aceptar un campo `parameters` que contenga un mapa de valores de parámetros.
   El esquema de Pulsar para la solicitud de inicio de flujo debe actualizarse para incluir el campo opcional `parameters`.
   Ejemplo de solicitud:
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

2. **Operación Get-Flow**
   El esquema de Pulsar para la respuesta de get-flow debe actualizarse para incluir el campo `parameters`
   Esto permite a los clientes recuperar los valores de los parámetros que se utilizaron cuando se inició el flujo.
   Ejemplo de respuesta:
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

#### Implementación del Servicio de Flujo

El servicio de configuración de flujo (`trustgraph-flow/trustgraph/config/service/flow.py`) requiere las siguientes mejoras:

1. **Función de Resolución de Parámetros**
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

   Esta función debe:
   Extraer los metadatos de los parámetros de la sección `parameters` del plano de flujo.
<<<<<<< HEAD
   Para cada parámetro, obtener la definición de tipo de la tienda de configuración.
=======
   Para cada parámetro, obtener la definición de tipo del almacén de configuración.
>>>>>>> 82edf2d (New md files from RunPod)
   Aplicar los valores predeterminados para cualquier parámetro que no sea proporcionado por el usuario.
   Manejar las relaciones de herencia de `controlled-by`.
   Devolver el conjunto de parámetros completo.

2. **Método `handle_start_flow` Modificado**
   Llamar a `resolve_parameters` después de cargar el plano de flujo.
   Utilizar el conjunto de parámetros resuelto completo para la sustitución de plantillas.
   Almacenar el conjunto de parámetros completo (no solo los proporcionados por el usuario) con el flujo.
   Validar que todos los parámetros requeridos tengan valores.

3. **Obtención del Tipo de Parámetro**
   Las definiciones de tipo de parámetro se almacenan en la configuración con el tipo "parameter-type".
<<<<<<< HEAD
   Cada definición de tipo contiene un esquema, un valor predeterminado y reglas de validación.
=======
   Cada definición de tipo contiene el esquema, el valor predeterminado y las reglas de validación.
>>>>>>> 82edf2d (New md files from RunPod)
   Almacenar en caché los tipos de parámetro utilizados con frecuencia para reducir las búsquedas en la configuración.

#### Integración del Sistema de Configuración

3. **Almacenamiento de Objetos de Flujo**
<<<<<<< HEAD
   Cuando un flujo se agrega al sistema de configuración por el componente de flujo en el administrador de configuración, el objeto de flujo debe incluir los valores de parámetros resueltos.
   El administrador de configuración debe almacenar tanto los parámetros originales proporcionados por el usuario como los valores resueltos (con los valores predeterminados aplicados).
   Los objetos de flujo en el sistema de configuración deben incluir:
     `parameters`: Los valores de parámetros resueltos finales utilizados para el flujo.
=======
   Cuando un flujo se agrega al sistema de configuración por el componente de flujo en el administrador de configuración, el objeto de flujo debe incluir los valores de parámetro resueltos.
   El administrador de configuración debe almacenar tanto los parámetros originales proporcionados por el usuario como los valores resueltos (con los valores predeterminados aplicados).
   Los objetos de flujo en el sistema de configuración deben incluir:
     `parameters`: Los valores de parámetro resueltos finales utilizados para el flujo.
>>>>>>> 82edf2d (New md files from RunPod)

#### Integración de la CLI

4. **Comandos de la CLI de la Biblioteca**
   Los comandos de la CLI que inician flujos necesitan soporte de parámetros:
<<<<<<< HEAD
     Aceptar valores de parámetros a través de indicadores de línea de comandos o archivos de configuración.
=======
     Aceptar valores de parámetro a través de indicadores de línea de comandos o archivos de configuración.
>>>>>>> 82edf2d (New md files from RunPod)
     Validar los parámetros contra las definiciones del plano de flujo antes de la presentación.
     Soporte para la entrada de archivos de parámetros (JSON/YAML) para conjuntos de parámetros complejos.

   Los comandos de la CLI que muestran flujos deben mostrar información de parámetros:
<<<<<<< HEAD
     Mostrar los valores de parámetros utilizados cuando se inició el flujo.
     Mostrar los parámetros disponibles para un plano de flujo.
     Mostrar los esquemas y valores predeterminados de validación de parámetros.
=======
     Mostrar los valores de parámetro utilizados cuando se inició el flujo.
     Mostrar los parámetros disponibles para un plano de flujo.
     Mostrar los esquemas de validación y los valores predeterminados de los parámetros.
>>>>>>> 82edf2d (New md files from RunPod)

#### Integración de la Clase Base del Procesador

5. **Soporte de ParameterSpec**
   Las clases base del procesador deben admitir la sustitución de parámetros a través del mecanismo ParametersSpec existente.
   La clase ParametersSpec (ubicada en el mismo módulo que ConsumerSpec y ProducerSpec) debe mejorarse si es necesario para admitir la sustitución de plantillas de parámetros.
<<<<<<< HEAD
   Los procesadores deben poder invocar ParametersSpec para configurar sus parámetros con los valores de parámetros resueltos en el momento del lanzamiento del flujo.
   La implementación de ParametersSpec debe:
     Aceptar configuraciones de parámetros que contengan marcadores de posición de parámetros (por ejemplo, `{model}`, `{temperature}`).
     Admitir la sustitución de parámetros en tiempo de ejecución cuando se instancia el procesador.
     Validar que los valores sustituidos coincidan con los tipos y restricciones esperados.
     Proporcionar manejo de errores para referencias de parámetros faltantes o no válidos.
=======
   Los procesadores deben poder invocar ParametersSpec para configurar sus parámetros con los valores de parámetro resueltos en el momento del inicio del flujo.
   La implementación de ParametersSpec debe:
     Aceptar configuraciones de parámetros que contengan marcadores de posición de parámetros (por ejemplo, `{model}`, `{temperature}`).
     Admitir la sustitución de parámetros en tiempo de ejecución cuando se instancia el procesador.
     Validar que los valores sustituidos coincidan con los tipos y las restricciones esperadas.
     Proporcionar el manejo de errores para las referencias de parámetros faltantes o no válidas.
>>>>>>> 82edf2d (New md files from RunPod)

#### Reglas de Sustitución

Los parámetros utilizan el formato `{parameter-name}` en los parámetros del procesador.
Los nombres de los parámetros en los parámetros coinciden con las claves en la sección `parameters` del flujo.
La sustitución se produce junto con la sustitución de `{id}` y `{class}`.
<<<<<<< HEAD
Las referencias de parámetros no válidas dan como resultado errores en el momento del lanzamiento.
La validación de tipos se basa en la definición de parámetro almacenada de forma centralizada.
**IMPORTANTE**: Todos los valores de parámetros se almacenan y transmiten como cadenas.
=======
Las referencias de parámetros no válidas dan como resultado errores en el momento del inicio.
La validación de tipos se basa en la definición de parámetro almacenada de forma centralizada.
**IMPORTANTE**: Todos los valores de los parámetros se almacenan y transmiten como cadenas.
>>>>>>> 82edf2d (New md files from RunPod)
  Los números se convierten a cadenas (por ejemplo, `0.7` se convierte en `"0.7"`).
  Los booleanos se convierten a cadenas en minúsculas (por ejemplo, `true` se convierte en `"true"`).
  Esto es requerido por el esquema de Pulsar que define `parameters = Map(String())`.

Ejemplo de resolución:
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

## Estrategia de Pruebas

Pruebas unitarias para la validación del esquema de parámetros.
Pruebas de integración para la sustitución de parámetros en los parámetros del procesador.
Pruebas de extremo a extremo para el lanzamiento de flujos con diferentes valores de parámetros.
Pruebas de la interfaz de usuario para la generación y validación de formularios de parámetros.
Pruebas de rendimiento para flujos con muchos parámetros.
<<<<<<< HEAD
Casos extremos: parámetros faltantes, tipos no válidos, referencias de parámetros no definidos.

## Plan de Migración

1. El sistema debe seguir soportando planos de flujo sin parámetros
   declarados.
2. El sistema debe seguir soportando flujos sin parámetros especificados:
=======
Casos extremos: parámetros faltantes, tipos inválidos, referencias de parámetros no definidos.

## Plan de Migración

1. El sistema debe continuar admitiendo planos de flujo sin parámetros
   declarados.
2. El sistema debe continuar admitiendo flujos sin parámetros especificados:
>>>>>>> 82edf2d (New md files from RunPod)
   Esto funciona para flujos sin parámetros y para flujos con parámetros
   (que tienen valores predeterminados).

## Preguntas Abiertas

<<<<<<< HEAD
P: ¿Deben los parámetros soportar objetos anidados complejos o limitarse a tipos simples?
=======
P: ¿Deben los parámetros admitir objetos anidados complejos o limitarse a tipos simples?
>>>>>>> 82edf2d (New md files from RunPod)
R: Los valores de los parámetros se codificarán como cadenas, por lo que probablemente
   queremos limitarnos a cadenas.

P: ¿Se deben permitir los marcadores de posición de parámetros en los nombres de las colas o solo en
   los parámetros?
R: Solo en los parámetros para evitar inyecciones extrañas y casos límite.

P: ¿Cómo manejar los conflictos entre los nombres de los parámetros y las variables del sistema como
   `id` y `class`?
R: No es válido especificar "id" y "class" al iniciar un flujo.

<<<<<<< HEAD
P: ¿Debemos soportar parámetros calculados (derivados de otros parámetros)?
=======
P: ¿Debemos admitir parámetros calculados (derivados de otros parámetros)?
>>>>>>> 82edf2d (New md files from RunPod)
R: Solo la sustitución de cadenas para evitar inyecciones extrañas y casos límite.

## Referencias

Especificación de JSON Schema: https://json-schema.org/
<<<<<<< HEAD
Especificación de la Definición del Plano de Flujo: docs/tech-specs/flow-class-definition.md
=======
Especificación de la definición del plano de flujo: docs/tech-specs/flow-class-definition.md
>>>>>>> 82edf2d (New md files from RunPod)
