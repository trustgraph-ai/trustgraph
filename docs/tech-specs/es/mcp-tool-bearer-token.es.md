---
layout: default
title: "Especificación de autenticación de tokens Bearer para herramientas MCP"
parent: "Spanish (Beta)"
---

# Especificación de autenticación de tokens Bearer para herramientas MCP

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

> **⚠️ IMPORTANTE: SOLO PARA UN ÚNICO ARREGLO (SINGLE-TENANT)**
>
> Esta especificación describe un **mecanismo básico de autenticación a nivel de servicio** para herramientas MCP. **NO** es una solución de autenticación completa y **NO es adecuada** para:
> - Entornos multiusuario
> - Despliegues multi-inquilino (multi-tenant)
> - Autenticación federada
> - Propagación del contexto del usuario
> - Autorización por usuario
>
> Esta función proporciona **un único token estático por herramienta MCP**, compartido entre todos los usuarios y sesiones. Si necesita autenticación por usuario o por inquilino, esta no es la solución adecuada.

## Descripción general
**Nombre de la función**: Soporte de autenticación de tokens Bearer para herramientas MCP
**Autor**: Claude Code Assistant
**Fecha**: 2025-11-11
**Estado**: En desarrollo

### Resumen ejecutivo

Permite que las configuraciones de las herramientas MCP especifiquen tokens Bearer opcionales para autenticarse con servidores MCP protegidos. Esto permite que TrustGraph invoque de forma segura las herramientas MCP alojadas en servidores que requieren autenticación, sin modificar las interfaces de invocación de agentes o herramientas.

**IMPORTANTE**: Este es un mecanismo de autenticación básico diseñado para escenarios de autenticación de servicio a servicio en un único arreglo (single-tenant). **NO** es adecuado para:
Entornos multiusuario donde diferentes usuarios necesitan diferentes credenciales
Despliegues multi-inquilino (multi-tenant) que requieren aislamiento por inquilino
Escenarios de autenticación federada
Autenticación o autorización a nivel de usuario
Gestión dinámica de credenciales o actualización de tokens

Esta función proporciona un token Bearer estático y a nivel de sistema por configuración de herramienta MCP, compartido entre todos los usuarios e invocaciones de esa herramienta.

### Declaración del problema

Actualmente, las herramientas MCP solo pueden conectarse a servidores MCP accesibles públicamente. Muchos despliegues de MCP en producción requieren autenticación mediante tokens Bearer por motivos de seguridad. Sin soporte de autenticación:
Las herramientas MCP no pueden conectarse a servidores MCP protegidos
Los usuarios deben exponer los servidores MCP públicamente o implementar proxies inversos
No existe una forma estandarizada de pasar credenciales a las conexiones MCP
No se pueden aplicar las mejores prácticas de seguridad en los puntos finales de MCP

### Objetivos

[ ] Permitir que las configuraciones de las herramientas MCP especifiquen un parámetro opcional `auth-token`
[ ] Actualizar el servicio de la herramienta MCP para usar tokens Bearer al conectarse a servidores MCP
[ ] Actualizar las herramientas de la CLI para admitir la configuración/visualización de tokens de autenticación
[ ] Mantener la compatibilidad con versiones anteriores con configuraciones de MCP sin autenticación
[ ] Documentar las consideraciones de seguridad para el almacenamiento de tokens

### Objetivos no incluidos
Actualización dinámica de tokens o flujos OAuth (solo tokens estáticos)
Cifrado de tokens almacenados (la seguridad del sistema de configuración está fuera del alcance)
Métodos de autenticación alternativos (autenticación básica, claves API, etc.)
Validación o verificación de la fecha de caducidad de los tokens
**Autenticación por usuario**: Esta función **NO** admite credenciales específicas del usuario
**Aislamiento multi-inquilino (multi-tenant)**: Esta función **NO** proporciona gestión de tokens por inquilino
**Autenticación federada**: Esta función **NO** se integra con proveedores de identidad (SSO, OAuth, SAML, etc.)
**Autenticación con conocimiento del contexto**: Los tokens no se pasan en función del contexto del usuario o la sesión

## Antecedentes y contexto

### Estado actual
Las configuraciones de las herramientas MCP se almacenan en el grupo de configuración `mcp` con esta estructura:
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

El servicio de la herramienta MCP se conecta a los servidores utilizando `streamablehttp_client(url)` sin ningún encabezado de autenticación.

### Limitaciones

**Limitaciones del Sistema Actual:**
1. **Sin soporte de autenticación:** No se puede conectar a servidores MCP protegidos.
2. **Exposición de seguridad:** Los servidores MCP deben ser accesibles públicamente o utilizar solo seguridad a nivel de red.
3. **Problemas de implementación en producción:** No se pueden seguir las mejores prácticas de seguridad para los puntos finales de la API.

**Limitaciones de Esta Solución:**
1. **Solo para un único inquilino:** Un token estático por herramienta MCP, compartido entre todos los usuarios.
2. **Sin credenciales por usuario:** No se puede autenticar como diferentes usuarios ni pasar el contexto del usuario.
3. **Sin soporte para múltiples inquilinos:** No se pueden aislar las credenciales por inquilino u organización.
4. **Solo tokens estáticos:** No hay soporte para la renovación, rotación o manejo de la expiración de los tokens.
5. **Autenticación a nivel de servicio:** Autentica el servicio TrustGraph, no a usuarios individuales.
6. **Contexto de seguridad compartido:** Todas las invocaciones de una herramienta MCP utilizan la misma credencial.

### Aplicabilidad del Caso de Uso

**✅ Casos de Uso Apropiados:**
Implementaciones de TrustGraph de un solo inquilino.
Autenticación de servicio a servicio (TrustGraph → Servidor MCP).
Entornos de desarrollo y pruebas.
Herramientas MCP internas a las que accede el sistema TrustGraph.
Escenarios en los que todos los usuarios comparten el mismo nivel de acceso a la herramienta MCP.
Credenciales de servicio estáticas y de larga duración.

**❌ Casos de Uso Inapropiados:**
Sistemas multiusuario que requieren autenticación por usuario.
Implementaciones SaaS multiinquilino con requisitos de aislamiento de inquilinos.
Escenarios de autenticación federada (SSO, OAuth, SAML).
Sistemas que requieren la propagación del contexto del usuario a los servidores MCP.
Entornos que necesitan la renovación dinámica de tokens o tokens de corta duración.
Aplicaciones donde diferentes usuarios necesitan diferentes niveles de permisos.
Requisitos de cumplimiento para registros de auditoría a nivel de usuario.

**Ejemplo de Escenario Apropiado:**
Una implementación de TrustGraph de una sola organización donde todos los empleados utilizan la misma herramienta MCP interna (por ejemplo, búsqueda de bases de datos de la empresa). El servidor MCP requiere autenticación para evitar el acceso externo, pero todos los usuarios internos tienen el mismo nivel de acceso.

**Ejemplo de Escenario Inapropiado:**
Una plataforma SaaS multiinquilino de TrustGraph donde el inquilino A y el inquilino B necesitan acceder a sus propios servidores MCP aislados con credenciales separadas. Esta función NO admite la administración de tokens por inquilino.

### Componentes Relacionados
**trustgraph-flow/trustgraph/agent/mcp_tool/service.py**: Servicio de invocación de la herramienta MCP.
**trustgraph-cli/trustgraph/cli/set_mcp_tool.py**: Herramienta de línea de comandos para crear/actualizar configuraciones de MCP.
**trustgraph-cli/trustgraph/cli/show_mcp_tools.py**: Herramienta de línea de comandos para mostrar configuraciones de MCP.
**SDK de Python para MCP**: `streamablehttp_client` de `mcp.client.streamable_http`

## Requisitos

### Requisitos Funcionales

1. **Token de Autenticación de la Configuración de MCP:** Las configuraciones de la herramienta MCP DEBEN admitir un campo opcional `auth-token`.
2. **Uso del Token Bearer:** El servicio de la herramienta MCP DEBE enviar el encabezado `Authorization: Bearer {token}` cuando se configure un token de autenticación.
3. **Soporte de la CLI:** `tg-set-mcp-tool` DEBE aceptar un parámetro opcional `--auth-token`.
4. **Visualización del Token:** `tg-show-mcp-tools` DEBE indicar cuándo se ha configurado un token de autenticación (enmascarado por motivos de seguridad).
5. **Compatibilidad con versiones anteriores:** Las configuraciones de la herramienta MCP existentes sin un token de autenticación DEBEN seguir funcionando.

### Requisitos No Funcionales
1. **Compatibilidad con versiones anteriores:** No hay cambios disruptivos para las configuraciones de la herramienta MCP existentes.
2. **Rendimiento:** No hay un impacto significativo en el rendimiento de la invocación de la herramienta MCP.
3. **Seguridad:** Los tokens se almacenan en la configuración (documentar las implicaciones de seguridad).

### Historias de Usuario

1. Como **ingeniero de DevOps**, quiero configurar tokens de portador para las herramientas MCP para que pueda asegurar los puntos finales del servidor MCP.
2. Como **usuario de la CLI**, quiero establecer tokens de autenticación al crear herramientas MCP para que pueda conectarme a servidores protegidos.
3. Como **administrador del sistema**, quiero ver qué herramientas MCP tienen la autenticación configurada para que pueda auditar la configuración de seguridad.

## Diseño

### Arquitectura de Alto Nivel
Extender la configuración y el servicio de la herramienta MCP para admitir la autenticación con token de portador:
1. Agregar un campo opcional `auth-token` al esquema de configuración de la herramienta MCP.
2. Modificar el servicio de la herramienta MCP para leer el token de autenticación y pasarlo al cliente HTTP.
3. Actualizar las herramientas de la CLI para admitir la configuración y visualización de tokens de autenticación.
4. Documentar las consideraciones de seguridad y las mejores prácticas.

### Esquema de Configuración

**Esquema Actual:**
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

**Nuevo Esquema** (con token de autenticación opcional):
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api",
  "auth-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Descripciones de campos:**
`remote-name` (opcional): Nombre utilizado por el servidor MCP (por defecto, la clave de configuración).
`url` (obligatorio): URL del punto final del servidor MCP.
`auth-token` (opcional): Token de tipo Bearer para la autenticación.

### Flujo de datos

1. **Almacenamiento de la configuración:** El usuario ejecuta `tg-set-mcp-tool --id my-tool --tool-url http://server/api --auth-token xyz123`.
2. **Carga de la configuración:** El servicio de la herramienta MCP recibe la actualización de la configuración a través de la devolución de llamada `on_mcp_config()`.
3. **Invocación de la herramienta:** Cuando se invoca la herramienta:
   El servicio lee `auth-token` de la configuración (si está presente).
   Crea un diccionario de encabezados: `{"Authorization": "Bearer {token}"}`.
   Pasa los encabezados a `streamablehttp_client(url, headers=headers)`.
   El servidor MCP valida el token y procesa la solicitud.

### Cambios en la API
No hay cambios en la API externa, solo una extensión del esquema de configuración.

### Detalles del componente

#### Componente 1: service.py (Servicio de la herramienta MCP)
**Archivo:** `trustgraph-flow/trustgraph/agent/mcp_tool/service.py`

**Propósito:** Invocar herramientas MCP en servidores remotos.

**Cambios requeridos** (en el método `invoke_tool()`):
1. Comprobar si `auth-token` está presente en la configuración `self.mcp_services[name]`.
2. Crear un diccionario de encabezados con el encabezado de autorización si existe un token.
3. Pasar los encabezados a `streamablehttp_client(url, headers=headers)`.

**Código actual** (líneas 42-89):
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server
        async with streamablehttp_client(url) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method
```

**Código Modificado**:
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        # Build headers with optional bearer token
        headers = {}
        if "auth-token" in self.mcp_services[name]:
            token = self.mcp_services[name]["auth-token"]
            headers["Authorization"] = f"Bearer {token}"

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server with headers
        async with streamablehttp_client(url, headers=headers) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method (unchanged)
```

#### Componente 2: set_mcp_tool.py (Herramienta de Configuración de Línea de Comandos)
**Archivo**: `trustgraph-cli/trustgraph/cli/set_mcp_tool.py`

**Propósito**: Crear/actualizar configuraciones de la herramienta MCP.

**Cambios Requeridos**:
1. Agregar un argumento opcional `--auth-token` a argparse.
2. Incluir `auth-token` en el archivo JSON de configuración cuando se proporciona.

**Argumentos Actuales**:
`--id` (requerido): Identificador de la herramienta MCP.
`--remote-name` (opcional): Nombre de la herramienta MCP remota.
`--tool-url` (requerido): Punto final de la URL de la herramienta MCP.
`-u, --api-url` (opcional): URL de la API de TrustGraph.

**Nuevo Argumento**:
`--auth-token` (opcional): Token Bearer para la autenticación.

**Construcción de Configuración Modificada**:
```python
# Build configuration object
config = {
    "url": args.tool_url,
}

if args.remote_name:
    config["remote-name"] = args.remote_name

if args.auth_token:
    config["auth-token"] = args.auth_token

# Store configuration
api.config().put([
    ConfigValue(type="mcp", key=args.id, value=json.dumps(config))
])
```

#### Componente 3: show_mcp_tools.py (Herramienta de visualización de línea de comandos)
**Archivo**: `trustgraph-cli/trustgraph/cli/show_mcp_tools.py`

**Propósito**: Mostrar configuraciones de la herramienta MCP.

**Cambios requeridos**:
1. Agregar columna "Auth" a la tabla de salida.
2. Mostrar "Sí" o "No" según la presencia de un token de autenticación.
3. No mostrar el valor real del token (seguridad).

**Salida actual**:
```
ID          Remote Name    URL
----------  -------------  ------------------------
my-tool     my-tool        http://server:3000/api
```

**Nueva Salida**:
```
ID          Remote Name    URL                      Auth
----------  -------------  ------------------------ ------
my-tool     my-tool        http://server:3000/api   Yes
other-tool  other-tool     http://other:3000/api    No
```

#### Componente 4: Documentación
**Archivo**: `docs/cli/tg-set-mcp-tool.md`

**Cambios Requeridos**:
1. Documentar el nuevo parámetro `--auth-token`
2. Proporcionar un ejemplo de uso con autenticación
3. Documentar las consideraciones de seguridad

## Plan de Implementación

### Fase 1: Crear Especificación Técnica
[x] Escribir una especificación técnica completa que documente todos los cambios

### Fase 2: Actualizar el Servicio MCP Tool
[ ] Modificar `invoke_tool()` en `service.py` para leer el token de autenticación desde la configuración
[ ] Construir un diccionario de encabezados y pasarlo a `streamablehttp_client`
[ ] Probar con un servidor MCP autenticado

### Fase 3: Actualizar las Herramientas CLI
[ ] Agregar el argumento `--auth-token` a `set_mcp_tool.py`
[ ] Incluir el token de autenticación en la configuración JSON
[ ] Agregar una columna "Auth" a la salida de `show_mcp_tools.py`
[ ] Probar los cambios de la herramienta CLI

### Fase 4: Actualizar la Documentación
[ ] Documentar el parámetro `--auth-token` en `tg-set-mcp-tool.md`
[ ] Agregar una sección de consideraciones de seguridad
[ ] Proporcionar un ejemplo de uso

### Fase 5: Pruebas
[ ] Probar que la herramienta MCP se conecta correctamente con el token de autenticación
[ ] Probar la compatibilidad con versiones anteriores (las herramientas sin token de autenticación aún funcionan)
[ ] Probar que las herramientas CLI aceptan y almacenan correctamente el token de autenticación
[ ] Probar que el comando "show" muestra el estado de la autenticación correctamente

### Resumen de Cambios en el Código
| Archivo | Tipo de Cambio | Líneas | Descripción |
|------|------------|-------|-------------|
| `service.py` | Modificado | ~52-66 | Agregar la lectura del token de autenticación y la construcción de encabezados |
| `set_mcp_tool.py` | Modificado | ~30-60 | Agregar el argumento --auth-token y el almacenamiento en la configuración |
| `show_mcp_tools.py` | Modificado | ~40-70 | Agregar la columna Auth a la visualización |
| `tg-set-mcp-tool.md` | Modificado | Varios | Documentar el nuevo parámetro |

## Estrategia de Pruebas

### Pruebas Unitarias
**Lectura del Token de Autenticación**: Probar que `invoke_tool()` lee correctamente el token de autenticación desde la configuración
**Construcción de Encabezados**: Probar que el encabezado de Autorización se construye correctamente con el prefijo Bearer
**Compatibilidad con Versiones Anteriores**: Probar que las herramientas sin token de autenticación funcionan sin cambios
**Análisis de Argumentos de la CLI**: Probar que el argumento `--auth-token` se analiza correctamente

### Pruebas de Integración
**Conexión Autenticada**: Probar que el servicio de la herramienta MCP se conecta a un servidor autenticado
**De Extremo a Extremo**: Probar el flujo CLI → almacenamiento de configuración → invocación del servicio con el token de autenticación
**Token No Requerido**: Probar que la conexión a un servidor no autenticado aún funciona

### Pruebas Manuales
**Servidor MCP Real**: Probar con un servidor MCP real que requiere la autenticación con token Bearer
**Flujo de Trabajo de la CLI**: Probar el flujo de trabajo completo: configurar la herramienta con la autenticación → invocar la herramienta → verificar el éxito
**Enmascaramiento de la Autenticación**: Verificar que el estado de la autenticación se muestra, pero el valor del token no se expone

## Migración e Implementación

### Estrategia de Migración
No se requiere migración: esta es una funcionalidad puramente adicional:
Las configuraciones existentes de la herramienta MCP que no tienen `auth-token` siguen funcionando sin cambios
Las nuevas configuraciones pueden incluir opcionalmente el campo `auth-token`
Las herramientas CLI aceptan, pero no requieren, el parámetro `--auth-token`

### Plan de Implementación
1. **Fase 1**: Implementar los cambios principales del servicio en el entorno de desarrollo/pruebas
2. **Fase 2**: Implementar las actualizaciones de las herramientas CLI
3. **Fase 3**: Actualizar la documentación
4. **Fase 4**: Implementación en producción con monitoreo

### Plan de Reversión
Los cambios principales son compatibles con versiones anteriores: las herramientas existentes no se ven afectadas
Si surgen problemas, el manejo del token de autenticación se puede deshabilitar eliminando la lógica de construcción de encabezados
Los cambios de la CLI son independientes y se pueden revertir por separado

## Consideraciones de Seguridad

### ⚠️ Limitación Crítica: Solo Autenticación de Un Solo Inquilino

**Este mecanismo de autenticación NO es adecuado para entornos multiusuario o multiinquilino.**

**Credenciales compartidas**: Todos los usuarios e invocaciones comparten el mismo token por herramienta MCP
**Sin contexto de usuario**: El servidor MCP no puede distinguir entre diferentes usuarios de TrustGraph
**Sin aislamiento de inquilinos**: Todos los inquilinos comparten la misma credencial para cada herramienta MCP
**Limitación del registro de auditoría**: El servidor MCP muestra todas las solicitudes de la misma credencial
**Ámbito de permisos**: No se pueden hacer cumplir diferentes niveles de permiso para diferentes usuarios

**NO use esta función si:**
Su implementación de TrustGraph sirve a múltiples organizaciones (multiinquilino)
Necesita realizar un seguimiento de qué usuario accedió a qué herramienta MCP
Diferentes usuarios requieren diferentes niveles de permiso
Necesita cumplir con los requisitos de auditoría a nivel de usuario
Su servidor MCP aplica límites de velocidad o cuotas por usuario

**Soluciones alternativas para escenarios multiusuario/multitenant:**
Implementar la propagación del contexto del usuario a través de encabezados personalizados
Implementar instancias de TrustGraph separadas por tenant
Utilizar aislamiento a nivel de red (VPCs, service meshes)
Implementar una capa de proxy que gestione la autenticación por usuario

### Almacenamiento de tokens
**Riesgo**: Los tokens de autenticación se almacenan en texto plano en el sistema de configuración

**Mitigación**:
Documentar que los tokens se almacenan sin cifrar
Recomendar el uso de tokens de corta duración siempre que sea posible
Recomendar un control de acceso adecuado en el almacenamiento de la configuración
Considerar una mejora futura para el almacenamiento de tokens cifrados

### Exposición de tokens
**Riesgo**: Los tokens podrían exponerse en registros o en la salida de la línea de comandos

**Mitigación**:
No registrar los valores de los tokens (solo registrar "autenticación configurada: sí/no")
El comando "show" de la línea de comandos muestra solo el estado enmascarado, no el token real
No incluir tokens en los mensajes de error

### Seguridad de la red
**Riesgo**: Los tokens se transmiten a través de conexiones no cifradas

**Mitigación**:
Documentar la recomendación de utilizar URL HTTPS para los servidores MCP
Advertir a los usuarios sobre el riesgo de transmisión en texto plano con HTTP

### Acceso a la configuración
**Riesgo**: El acceso no autorizado al sistema de configuración expone los tokens

**Mitigación**:
Documentar la importancia de asegurar el acceso al sistema de configuración
Recomendar el principio de mínimo privilegio para el acceso a la configuración
Considerar el registro de auditoría para los cambios de configuración (mejora futura)

### Entornos multiusuario
**Riesgo**: En las implementaciones multiusuario, todos los usuarios comparten las mismas credenciales de MCP

**Comprensión del riesgo**:
El usuario A y el usuario B utilizan el mismo token al acceder a una herramienta de MCP
El servidor MCP no puede distinguir entre diferentes usuarios de TrustGraph
No hay forma de aplicar permisos o límites de velocidad por usuario
Los registros de auditoría en el servidor MCP muestran todas las solicitudes del mismo identificador
Si la sesión de un usuario se ve comprometida, el atacante tiene el mismo acceso a MCP que todos los usuarios

**Esto NO es un error; es una limitación fundamental de este diseño.**

## Impacto en el rendimiento
**Bajo sobrecosto**: La construcción de encabezados agrega un tiempo de procesamiento insignificante
**Impacto en la red**: El encabezado HTTP adicional agrega ~50-200 bytes por solicitud
**Uso de memoria**: Aumento insignificante para almacenar la cadena de token en la configuración

## Documentación

### Documentación para el usuario
[ ] Actualizar `tg-set-mcp-tool.md` con el parámetro `--auth-token`
[ ] Agregar una sección de consideraciones de seguridad
[ ] Proporcionar un ejemplo de uso con un token de tipo "bearer"
[ ] Documentar las implicaciones del almacenamiento de tokens

### Documentación para el desarrollador
[ ] Agregar comentarios en línea para el manejo de tokens de autenticación en `service.py`
[ ] Documentar la lógica de construcción de encabezados
[ ] Actualizar la documentación del esquema de configuración de la herramienta MCP

## Preguntas abiertas
1. **Cifrado de tokens**: ¿Debemos implementar el almacenamiento de tokens cifrados en el sistema de configuración?
2. **Actualización de tokens**: ¿Soporte futuro para flujos de actualización de OAuth o rotación de tokens?
3. **Métodos de autenticación alternativos**: ¿Debemos admitir la autenticación básica, las claves API u otros métodos?

## Alternativas consideradas

1. **Variables de entorno para tokens**: Almacenar tokens en variables de entorno en lugar de en la configuración
   **Rechazada**: Complica la implementación y la gestión de la configuración

2. **Almacén de secretos separado**: Utilizar un sistema de gestión de secretos dedicado
   **Aplazada**: Fuera del alcance de la implementación inicial, considerar una mejora futura

3. **Múltiples métodos de autenticación**: Admitir Basic, API key, OAuth, etc.
   **Rechazada**: Los tokens de tipo "bearer" cubren la mayoría de los casos de uso, mantener la implementación inicial simple

4. **Almacenamiento de tokens cifrado**: Cifrar los tokens en el sistema de configuración
   **Aplazada**: La seguridad del sistema de configuración es una preocupación más amplia, posponer a un trabajo futuro

5. **Tokens por invocación**: Permitir que los tokens se pasen en el momento de la invocación
   **Rechazada**: Viola la separación de responsabilidades, el agente no debe manejar las credenciales

## Referencias
[Especificación del protocolo MCP](https://github.com/modelcontextprotocol/spec)
[Autenticación Bearer HTTP (RFC 6750)](https://tools.ietf.org/html/rfc6750)
[Servicio de la herramienta MCP actual](../trustgraph-flow/trustgraph/agent/mcp_tool/service.py)
[Especificación de argumentos de la herramienta MCP](./mcp-tool-arguments.md)

## Apéndice

### Ejemplo de uso

**Configuración de la herramienta MCP con autenticación:**
```bash
tg-set-mcp-tool \
  --id secure-tool \
  --tool-url https://secure-server.example.com/mcp \
  --auth-token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Mostrando herramientas de MCP:**
```bash
tg-show-mcp-tools

ID            Remote Name   URL                                    Auth
-----------   -----------   ------------------------------------   ------
secure-tool   secure-tool   https://secure-server.example.com/mcp  Yes
public-tool   public-tool   http://localhost:3000/mcp              No
```

### Ejemplo de configuración

**Almacenado en el sistema de configuración**:
```json
{
  "type": "mcp",
  "key": "secure-tool",
  "value": "{\"url\": \"https://secure-server.example.com/mcp\", \"auth-token\": \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\"}"
}
```

### Mejores prácticas de seguridad

1. **Utilice HTTPS**: Siempre utilice URL HTTPS para los servidores MCP con autenticación
2. **Tokens de corta duración**: Utilice tokens con fecha de caducidad siempre que sea posible
3. **Privilegios mínimos**: Conceda a los tokens los permisos mínimos requeridos
4. **Control de acceso**: Restrinja el acceso al sistema de configuración
5. **Rotación de tokens**: Rote los tokens regularmente
6. **Registro de auditoría**: Supervise los cambios de configuración para detectar eventos de seguridad
