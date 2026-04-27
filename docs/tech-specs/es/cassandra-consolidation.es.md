---
layout: default
title: "Especificación Técnica: Consolidación de la Configuración de Cassandra"
parent: "Spanish (Beta)"
---

# Especificación Técnica: Consolidación de la Configuración de Cassandra

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**Estado:** Borrador
**Autor:** Asistente
**Fecha:** 2024-09-03

## Visión General

Esta especificación aborda los patrones de nombres y configuración inconsistentes para los parámetros de conexión de Cassandra en todo el código base de TrustGraph. Actualmente, existen dos esquemas de nombres de parámetros diferentes (`cassandra_*` frente a `graph_*`), lo que provoca confusión y complejidad en el mantenimiento.

## Declaración del Problema

El código base actualmente utiliza dos conjuntos distintos de parámetros de configuración de Cassandra:

1. **Módulos de Conocimiento/Config/Biblioteca** utilizan:
   - `cassandra_host` (lista de hosts)
   - `cassandra_usuario`
   - `cassandra_contraseña`

2. **Módulos de Gráficos/Almacenamiento** utilizan:
   - `graph_host` (único host, a veces convertido en lista)
   - `graph_username`
   - `graph_password`

3. **Exposición inconsistente de la línea de comandos:**
   - Algunos procesadores (p. ej., `kg-store`) no expone la configuración de Cassandra como argumentos de línea de comandos
   - Otros procesadores los expone con nombres y formatos diferentes
   - El texto de ayuda no refleja los valores predeterminados de las variables de entorno

Ambos conjuntos de parámetros se conectan al mismo clúster de Cassandra, pero con diferentes convenciones de nombres, lo que provoca:
- Confusión en la configuración para los usuarios
- Mayor carga de mantenimiento
- Documentación inconsistente
- Posibilidad de configuración incorrecta
- Incapacidad de anular la configuración mediante argumentos de línea de comandos en algunos procesadores

## Solución Propuesta

### 1. Estandarizar los Nombres de los Parámetros

Todos los módulos utilizarán nombres de parámetros consistentes `cassandra_*`:
- `cassandra_host` - Lista de hosts (almacenado internamente como lista)
- `cassandra_username` - Nombre de usuario para la autenticación
- `cassandra_contraseña` - Contraseña para la autenticación

### 2. Argumentos de Línea de Comandos

Todos los procesadores DEBEN exponer la configuración de Cassandra a través de argumentos de línea de comandos:
- `--cassandra-host` - Lista separada por comas de hosts
- `--cassandra-username` - Nombre de usuario para la autenticación
- `--cassandra-password` - Contraseña para la autenticación

### 3. Fallback de Variables de Entorno

Si los parámetros de la línea de comandos no se proporcionan explícitamente, el sistema verificará las variables de entorno:
- `CASSANDRA_HOST` - Lista separada por comas de hosts
- `CASSANDRA_USERNAME` - Nombre de usuario para la autenticación
- `CASSANDRA_PASSWORD` - Contraseña para la autenticación

### 4. Valores Predeterminados

Si ni los parámetros de la línea de comandos ni las variables de entorno no se especifican:
- `cassandra_host` se establece en `["cassandra"]`
- `cassandra_username` se establece en `None` (sin autenticación)
- `cassandra_password` se establece en `None` (sin autenticación)

### 5. Requisitos de Ayuda

La salida `--help` DEBE:
- Mostrar los valores predeterminados de las variables de entorno
- Nunca mostrar los valores de la contraseña (mostrar `****` o `<set>` en su lugar)
- Indicar claramente el orden de resolución en la ayuda

Ejemplo de salida de ayuda:
```
--cassandra-host HOST
    Lista de hosts de Cassandra, separada por comas (predeterminado: prod-cluster-1,prod-cluster-2)
    [desde la variable de entorno CASSANDRA_HOST]

--cassandra-username USERNAME
    Nombre de usuario de Cassandra (predeterminado: cassandra_user)
    [desde la variable de entorno CASSANDRA_USERNAME]

--cassandra-password PASSWORD
    Contraseña de Cassandra (predeterminado: <establecido desde el entorno>)
```

## Detalles de Implementación

### Orden de Resolución
Para cada parámetro de Cassandra, el orden de resolución será:
1. Valor del argumento de la línea de comandos
2. Variable de entorno (`CASSANDRA_*`)
3. Valor predeterminado

### Manejo del parámetro Host
El parámetro `cassandra_host`:
- La línea de comandos acepta una cadena separada por comas: `--cassandra-host "host1,host2,host3"`
- La variable de entorno acepta una cadena separada por comas: `CASSANDRA_HOST="host1,host2,host3"`
- Internamente siempre se almacena como una lista: `["host1", "host2", "host3"]`

### Código de Ejemplo
```python
# Código antiguo
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help='Host del gráfico (predeterminado: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help='Nombre de usuario de Cassandra'
    )

# Código nuevo
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Usa el asistente estándar
```

### Actualización de Módulos que Utilizan `graph_*` Parámetros
1. Cambiar los nombres de los parámetros de `graph_*` a `cassandra_*`
2. Reemplazar los métodos `add_args()` personalizados
3. Utilizar las funciones `add_cassandra_args()` estándar
4. Actualizar las cadenas de documentación

Ejemplo de transformación:
```python
# Código antiguo
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help=f'Host del gráfico (predeterminado: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help=f'Nombre de usuario de Cassandra'
    )

# Código nuevo
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Usa el asistente estándar
```

### Actualización de Módulos que Utilizan `cassandra_*` Parámetros
1. Agregar soporte para argumentos de línea de comandos (p. ej., `kg-store`)
2. Reemplazar las definiciones de argumentos existentes con `add_cassandra_args()`
3. Utilizar las funciones `resolve_cassandra_config()` para una resolución consistente
4. Asegurar el manejo consistente de las listas de hosts

### Actualización de Pruebas y Documentación
1. Actualizar todos los archivos de prueba
2. Actualizar la documentación de la línea de comandos
3. Actualizar la documentación de la API
4. Actualizar los ejemplos de Docker Compose
5. Actualizar la documentación de referencia de la configuración

## Compatibilidad con versiones anteriores

Para mantener la compatibilidad con versiones anteriores durante la transición:

1. **Advertencias de desuso** para los parámetros `graph_*`
2. **Alias de parámetros** - aceptar nombres antiguos y nuevos inicialmente
3. **Implementación gradual** durante varios lanzamientos
4. **Actualizaciones de documentación** con guía de migración

Ejemplo de código para la compatibilidad con versiones anteriores:
```python
def __init__(self, **params):
    # Manejar parámetros graph_* desactualizados
    if 'graph_host' in params:
        warnings.warn("graph_host está desactualizado, usa cassandra_host", DeprecationWarning)
        params.setdefault('cassandra_host', params.pop('graph_host'))

    if 'graph_username' in params:
        warnings.warn("graph_username está desactualizado, usa cassandra_username", DeprecationWarning)
        params.setdefault('cassandra_username', params.pop('graph_username'))

    # ... continuar con la resolución estándar
```

## Estrategia de Pruebas

1. **Pruebas unitarias** para la lógica de resolución de la configuración
2. **Pruebas de integración** con diversas combinaciones de configuración
3. **Pruebas de variables de entorno**
4. **Pruebas de compatibilidad con versiones anteriores** con parámetros desactualizados
5. **Pruebas de Docker compose** con variables de entorno

## Actualizaciones de Documentación

1. Actualizar toda la documentación de la línea de comandos
2. Actualizar la documentación de la API
3. Crear una guía de migración
4. Actualizar los ejemplos de Docker Compose
5. Actualizar la documentación de referencia de la configuración

## Riesgos y Mitigación

| Riesgo | Impacto | Mitigación |
|------|--------|------------|
| Cambios que rompen para los usuarios | Alto | Implementar un período de compatibilidad con versiones anteriores |
| Confusión en la configuración durante la transición | Medio | Documentación clara y advertencias de desuso |
| Fallos de prueba | Medio | Actualizaciones exhaustivas de prueba |
| Problemas de implementación de Docker | Alto | Actualizar todos los ejemplos de Docker Compose |

## Criterios de Éxito

- [ ] Todos los módulos utilizan nombres de parámetros consistentes `cassandra_*`
- [ ] Todos los procesadores expone la configuración de Cassandra a través de argumentos de línea de comandos
- [ ] La salida de la ayuda muestra los valores predeterminados de las variables de entorno
- [ ] Los valores de la contraseña nunca se muestran en la ayuda
- [ ] La retroalimentación de las variables de entorno funciona correctamente
- [ ] El parámetro `cassandra_host` se gestiona de forma consistente como una lista internamente
- [ ] Se mantiene la compatibilidad con versiones anteriores durante al menos 2 lanzamientos
- [ ] Todas las pruebas pasan con el nuevo sistema de configuración
- [ ] La documentación está actualizada
- [ ] Los ejemplos de Docker Compose funcionan con las variables de entorno

## Cronograma

- **Semana 1:** Implementar el asistente de configuración común y actualizar los módulos que utilizan `graph_*`
- **Semana 2:** Agregar soporte de variable de entorno a los módulos existentes que utilizan `cassandra_*`
- **Semana 3:** Actualizar las cadenas de documentación
- **Semana 4:** Pruebas de integración y correcciones de errores

## Consideraciones Futuras

- Considerar extender este patrón a otras configuraciones de bases de datos (p. ej., Elasticsearch)
- Implementar la validación de la configuración y mejores mensajes de error
- Agregar soporte para la configuración de conexión de piscina (connection pooling)
- Considerar agregar soporte para archivos `.env`
