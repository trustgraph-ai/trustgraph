# Running Tests

## Setup

Create a virtual environment and install the required packages:

```bash
python3 -m venv venv
source venv/bin/activate
pip install ./trustgraph-base
pip install ./trustgraph-cli
pip install ./trustgraph-flow
pip install ./trustgraph-vertexai
pip install ./trustgraph-bedrock
pip install ./trustgraph-docling
pip install -r tests/requirements.txt
```

Do **not** use `pip install -e`. The overlapping `trustgraph` namespace
across multiple packages causes chaos with editable installs.

## Running

```bash
pytest tests/ -m 'not slow'
```
