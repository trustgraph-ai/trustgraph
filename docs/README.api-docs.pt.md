---
layout: default
title: "Geração automática de documentação"
parent: "Portuguese (Beta)"
---

# Geração automática de documentação

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Documentação da API REST e WebSocket

`specs/build-docs.sh` - Constrói a documentação REST e WebSocket a partir das
  especificações OpenAPI e AsyncAPI.

## Documentação da API Python

A documentação da API Python é gerada a partir de docstrings usando um script Python personalizado que inspeciona o pacote `trustgraph.api`.

### Pré-requisitos

O pacote trustgraph deve ser importável. Se você estiver trabalhando em um ambiente de desenvolvimento:

```bash
cd trustgraph-base
pip install -e .
```

### Gerando Documentação

A partir do diretório de documentação:

```bash
cd docs
python3 generate-api-docs.py > python-api.md
```

Isso gera um único arquivo Markdown com documentação completa da API, mostrando:
Instruções de instalação e guia de início rápido
Declarações de importação para cada classe/tipo
Documentação completa com exemplos
Sumário organizado por categoria

### Estilo da Documentação

Todas as documentações seguem o formato do Google:
Resumo breve de uma linha
Descrição detalhada
Seção "Args" com descrições dos parâmetros
Seção "Returns"
Seção "Raises" (quando aplicável)
Blocos de código de exemplo com realce de sintaxe adequado

A documentação gerada mostra a API pública exatamente como os usuários a importam de `trustgraph.api`, sem expor a estrutura interna do módulo.
