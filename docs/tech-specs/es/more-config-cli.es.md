---
layout: default
title: "Especificación Técnica de la CLI para Configuración"
parent: "Spanish (Beta)"
---

# Especificación Técnica de la CLI para Configuración

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Descripción general

Esta especificación describe las capacidades mejoradas de configuración a través de la línea de comandos para TrustGraph, lo que permite a los usuarios gestionar elementos de configuración individuales utilizando comandos CLI granulares. La integración soporta cuatro casos de uso principales:

1. **Listar Elementos de Configuración**: Mostrar las claves de configuración de un tipo específico.
2. **Obtener Elemento de Configuración**: Recuperar los valores de configuración específicos.
3. **Establecer Elemento de Configuración**: Establecer o actualizar elementos de configuración individuales.
4. **Eliminar Elemento de Configuración**: Eliminar elementos de configuración específicos.

## Objetivos

- **Control Granular**: Permitir la gestión de elementos de configuración individuales en lugar de operaciones masivas.
- **Listado Basado en Tipo**: Permitir a los usuarios explorar los elementos de configuración por tipo.
- **Operaciones en Elemento Individual**: Proporcionar comandos para obtener/establecer/eliminar elementos de configuración individuales.
- **Integración con API**: Aprovechar la API de Config existente para todas las operaciones.
- **Patrón CLI Consistente**: Seguir las convenciones y patrones CLI establecidos de TrustGraph.
- **Manejo de Errores**: Proporcionar mensajes de error claros para operaciones inválidas.
- **Salida JSON**: Soporte para salida estructurada para uso programático.
- **Documentación**: Incluir ayuda y ejemplos de uso completos.

## Antecedentes

Actualmente, TrustGraph proporciona la gestión de la configuración a través de la API de Config y un único comando de línea de comandos `tg-show-config` que muestra toda la configuración. Si bien esto funciona para la visualización de la configuración, carece de capacidades de gestión granular.

Las limitaciones actuales incluyen:
- No hay forma de listar los elementos de configuración por tipo desde la línea de comandos.
- No hay ningún comando de línea de comandos para recuperar valores de configuración específicos.
- No hay ningún comando de línea de comandos para establecer elementos de configuración individuales.
- No hay ningún comando de línea de comandos para eliminar elementos de configuración específicos.

Esta especificación aborda estas lagunas agregando cuatro nuevos comandos de línea de comandos que proporcionan la gestión de configuración granular. Al exponer las operaciones de la API de Config individual a través de comandos CLI, TrustGraph puede:
- Permitir la gestión de la configuración a través de scripts.
- Permitir la exploración de la estructura de la configuración por tipo.
- Soporte para actualizaciones de configuración dirigidas.
- Proporcionar un control granular de la configuración.

## Diseño Técnico

### Arquitectura

La configuración CLI mejorada requiere los siguientes componentes técnicos:

1. **tg-list-config-items**
   - Lista las claves de configuración para un tipo específico.
   - Llama al método de API `Config.list(type)`.
   - Salida la lista de claves de configuración.

   Módulo: `trustgraph.cli.list_config_items`

2. **tg-get-config-item**
   - Recupera el(los) elemento(s) de configuración específico(s).
   - Llama al método de API `Config.get([ConfigKey(type, key)])`.
   - Salida los valores de configuración en formato JSON.

   Módulo: `trustgraph.cli.get_config_item`

3. **tg-put-config-item**
   - Establece o actualiza un elemento de configuración.
   - Llama al método de API `Config.put([ConfigValue(type, key, value)])`.
   - Acepta los parámetros de tipo, clave y valor.

   Módulo: `trustgraph.cli.put_config_item`

4. **tg-delete-config-item**
   - Elimina un elemento de configuración.
   - Llama al método de API `Config.delete([ConfigKey(type, key)])`.
   - Acepta los parámetros de tipo y clave.

   Módulo: `trustgraph.cli.delete_config_item`

### Modelos de Datos

#### ConfigKey y ConfigValue

Los comandos utilizan las estructuras de datos existentes de `trustgraph.api.types`:

```python
@dataclasses.dataclass
class ConfigKey:
    type : str
    key : str

@dataclasses.dataclass
class ConfigValue:
    type : str
    key : str
    value : str
```

Esto permite:
- Manejo de datos consistente entre la CLI y la API.
- Operaciones de configuración seguras por tipo.
- Formatos de entrada/salida estructurados.
- Integración con la API de Config existente.

### Especificaciones de la CLI

#### tg-list-config-items
```bash
tg-list-config-items --type <tipo-de-configuración> [--formato texto|json] [--url-api <url>]
```
- **Propósito**: Listar todas las claves de configuración para un tipo dado.
- **Llamada a la API**: `Config.list(type)`
- **Salida**:
  - `texto` (predeterminado): Claves de configuración separadas por nuevas líneas.
  - `json`: Array JSON de claves de configuración.

#### tg-get-config-item
```bash
tg-get-config-item --type <tipo-de-configuración> --clave <clave> [--formato texto|json] [--url-api <url>]
```
- **Propósito**: Recuperar el elemento de configuración específico.
- **Llamada a la API**: `Config.get([ConfigKey(type, key)])`
- **Salida**:
  - `texto` (predeterminado): Cadena de texto sin comillas ni codificación.
  - `json`: Cadena de texto codificada en JSON.

#### tg-put-config-item
```bash
tg-put-config-item --type <tipo-de-configuración> --clave <clave> --valor <valor> [--url-api <url>]
tg-put-config-item --type <tipo-de-configuración> --clave <clave> --stdin [--url-api <url>]
```
- **Propósito**: Establecer o actualizar el elemento de configuración.
- **Llamada a la API**: `Config.put([ConfigValue(type, key, value)])`
- **Opciones de entrada**:
  - `--valor`: Valor de cadena proporcionado directamente en la línea de comandos.
  - `--stdin`: Leer todo el valor de entrada desde la entrada estándar como el valor del elemento de configuración.
- **Salida**: Confirmación de éxito

#### tg-delete-config-item
```bash
tg-delete-config-item --type <tipo-de-configuración> --clave <clave> [--url-api <url>]
```
- **Propósito**: Eliminar el elemento de configuración.
- **Llamada a la API**: `Config.delete([ConfigKey(type, key)])`
- **Salida**: Confirmación de éxito

### Detalles de Implementación

- Se debe usar un formato JSON para la salida de la API.
- Se debe usar un formato de texto sin comillas para la salida de la API.
- Se deben usar los parámetros de línea de comandos para especificar el tipo, la clave y el valor.
- Se debe proporcionar una confirmación de éxito para las operaciones de la línea de comandos.

## Preguntas Abiertas

- ¿Deberían los comandos admitir operaciones en lote (múltiples claves) además de elementos individuales?
- ¿Cuál debe ser el formato de salida para las confirmaciones de éxito?
- ¿Cómo deberían descubrir los usuarios los tipos de configuración?

## Referencias

- API de Config existente: `trustgraph/api/config.py`
- Patrones de CLI: `trustgraph-cli/trustgraph/cli/show_config.py`
- Tipos de datos: `trustgraph/api/types.py`
