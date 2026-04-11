---
layout: default
title: "Estrategia de Registro de TrustGraph"
parent: "Spanish (Beta)"
---

# Estrategia de Registro de TrustGraph

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visión general

TrustGraph utiliza el módulo integrado de Python `logging` para todas las operaciones de registro, con una configuración centralizada y la integración opcional de Loki para la agregación de registros. Esto proporciona un enfoque estandarizado y flexible para el registro en todos los componentes del sistema.

## Configuración predeterminada

### Nivel de registro
- **Nivel predeterminado**: `INFO`
- **Configurable a través de**: Argumento de línea de comandos `--log-level`
- **Opciones**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### Destinos de salida
1. **Consola (stdout)**: Siempre habilitado - asegura la compatibilidad con entornos contenedorizados
2. **Loki**: Agregación centralizada de registros opcional (habilitado por defecto, se puede deshabilitar)

## Módulo de registro centralizado

Todas las configuraciones de registro se gestionan mediante el módulo `trustgraph.base.logging`, que proporciona:
- `add_logging_args(parser)` - Agrega argumentos de línea de comandos estándar para registro
- `setup_logging(args)` - Configura el registro a partir de los argumentos analizados

Este módulo se utiliza en todos los componentes del lado del servidor:
- Servicios basados en AsyncProcessor
- API Gateway
- Servidor MCP

## Guía de implementación

### 1. Inicialización del registrador

Cada módulo debe crear su propio registrador utilizando el nombre del módulo:

```python
import logging

logger = logging.getLogger(__name__)
```

El nombre del registrador se utiliza automáticamente como etiqueta en Loki para filtrar y buscar.

### 2. Inicialización del servicio

Todos los servicios del lado del servidor obtienen automáticamente la configuración de registro a través del módulo centralizado:

```python
from trustgraph.base import add_logging_args, setup_logging
import argparse

def main():
    parser = argparse.ArgumentParser()

    # Agrega argumentos estándar de registro (incluida la configuración de Loki)
    add_logging_args(parser)

    # Agrega tus argumentos específicos del servicio
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()
    args = vars(args)

    # Configura el registro temprano en el inicio
    setup_logging(args)

    # Resto de la inicialización del servicio
    logger = logging.getLogger(__name__)
    logger.info("Servicio iniciado...")
```

### 3. Argumentos de línea de comandos

Todos los servicios admiten estos argumentos de registro:

**Nivel de registro:**
```bash
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
```

**Configuración de Loki:**
```bash
--loki-enabled              # Habilita Loki (predeterminado)
--no-loki-enabled           # Deshabilita Loki
--loki-url URL              # URL de envío a Loki (predeterminado: http://loki:3100/loki/api/v1/push)
--loki-username USERNAME    # Nombre de usuario opcional de autenticación
--loki-password PASSWORD    # Contraseña opcional de autenticación
```

**Ejemplos:**
```bash
# Predeterminado - nivel INFO, Loki habilitado
./my-service

# Modo DEBUG, solo consola
./my-service --log-level DEBUG --no-loki-enabled

# URL de Loki personalizada con autenticación
./my-service --loki-url http://loki.prod:3100/loki/api/v1/push \
             --loki-username admin --loki-password secret
```

### 4. Variables de entorno

La configuración de Loki admite los valores predeterminados de las variables de entorno:

```bash
export LOKI_URL=http://loki.prod:3100/loki/api/v1/push
export LOKI_USERNAME=admin
export LOKI_PASSWORD=secret
```

Los argumentos de la línea de comandos tienen prioridad sobre las variables de entorno.

### 5. Mejores prácticas de registro

#### Uso de los niveles de registro
- **DEBUG**: Información detallada para diagnosticar problemas (valores de variables, entrada/salida de funciones)
- **INFO**: Mensajes informativos generales (servicio iniciado, configuración cargada, hitos de procesamiento)
- **WARNING**: Mensajes de advertencia para situaciones potencialmente dañinas (características obsoletas, errores recuperables)
- **ERROR**: Mensajes de error para problemas serios (operaciones fallidas, excepciones)
- **CRITICAL**: Mensajes críticos para fallas del sistema que requieren atención inmediata

#### Formato de mensaje
```python
# Bueno - incluye contexto
logger.info(f"Procesando documento: {doc_id}, tamaño: {doc_size} bytes")
logger.error(f"No se pudo conectar a la base de datos: {error}", exc_info=True)

# No bueno - carece de contexto
logger.info("Procesando documento")
logger.error("Conexión fallida")
```

#### Consideraciones de rendimiento
```python
# Usa la incrustación para operaciones costosas
logger.debug("Resultado de la operación costosa: %s", expensive_function())

# Comprueba el nivel de registro para operaciones de depuración muy costosas
if logger.isEnabledFor(logging.DEBUG):
    debug_data = compute_expensive_debug_info()
    logger.debug(f"Datos de depuración: {debug_data}")
```

#### 6. Registro estructurado con Loki

Para datos complejos, usa el registro estructurado con etiquetas adicionales para Loki:

```python
logger.info("Solicitud procesada", extra={
    'tags': {
        'request_id': request_id,
        'user_id': user_id,
        'status': 'éxito'
    }
})
```

Estas etiquetas se convierten en etiquetas de búsqueda en Loki, además de las etiquetas automáticas:
- `severity` - Nivel de registro (DEBUG, INFO, etc.)
- `logger` - Nombre del módulo (del `__name__`)

### 7. Registro de excepciones

Siempre incluye trazas de pila para las excepciones:

```python
try:
    process_data()
except Exception as e:
    logger.error(f"No se pudo procesar los datos: {e}", exc_info=True)
```

### 8. Dependencias

El módulo centralizado de registro requiere:
- `python-logging-loki` - Para la integración de Loki (opcional, funciona si falta)

Ya incluido en `trustgraph-base/pyproject.toml` y `requirements.txt`.

## Migración

Para código existente:

1. **Servicios que ya utilizan AsyncProcessor**: No se necesita cambios, la integración de Loki es automática
2. **Servicios que no utilizan AsyncProcessor** (api-gateway, mcp-server): Ya actualizado
3. **Herramientas de línea de comandos**: Fuera del alcance - continúe usando `print()` o registro simple

### De `print()` a registro:
```python
# Antes
print(f"Procesando documento {doc_id}")

# Después
logger = logging.getLogger(__name__)
logger.info(f"Procesando documento {doc_id}")
```

## Resumen de configuración

| Argumento | Predeterminado | Variable de entorno | Descripción |
|---|---|---|---|
| `--log-level` | `INFO` | - | Nivel de registro en la consola y Loki |
| `--loki-enabled` | `True` | - | Habilita el registro de Loki |
| `--loki-url` | `http://loki:3100/loki/api/v1/push` | `LOKI_URL` | Puntero al API de Loki |
| `--loki-username` | `None` | `LOKI_USERNAME` | Nombre de usuario de autenticación para Loki |
| `--loki-password` | `None` | `LOKI_PASSWORD` | Contraseña de autenticación para Loki |
