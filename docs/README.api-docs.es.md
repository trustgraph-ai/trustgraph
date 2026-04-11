---
layout: default
title: "Generación automática de documentación"
parent: "Spanish (Beta)"
---

# Generación automática de documentación

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Documentación de la API REST y WebSocket

- `specs/build-docs.sh` - Genera la documentación de la API REST y WebSocket a partir de las especificaciones OpenAPI y AsyncAPI.

## Documentación de la API Python

La documentación de la API Python se genera a partir de los docstrings utilizando un script de Python personalizado que introspecciona el paquete `trustgraph.api`.

### Requisitos previos

El paquete `trustgraph` debe ser importable. Si estás trabajando en un entorno de desarrollo:

```bash
cd trustgraph-base
pip install -e .
```

### Generación de documentación

Desde el directorio `docs`:

```bash
cd docs
python3 generate-api-docs.py > python-api.md
```

Esto genera un único archivo Markdown con documentación de la API completa, mostrando:
- Guía de instalación y inicio rápido
- Declaraciones de importación para cada clase/tipo
- Docstrings completos con ejemplos
- Tabla de contenidos organizada por categoría

### Estilo de documentación

Todos los docstrings siguen el formato de Google:
- Resumen breve de una línea
- Descripción detallada
- Sección Args con descripciones de parámetros
- Sección Returns
- Sección Raises (cuando corresponda)
- Bloques de código de ejemplo con resaltado de sintaxis adecuado

La documentación generada muestra la API pública exactamente como los usuarios la importan desde `trustgraph.api`, sin exponer la estructura interna del módulo.
