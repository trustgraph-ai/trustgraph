#!/bin/bash
# Install TrustGraph packages for testing

echo "Installing TrustGraph packages..."

# Install base package first (required by others)
cd trustgraph-base
pip install -e .
cd ..

# Install base package first (required by others)
cd trustgraph-cli
pip install -e .
cd ..

# Install vertexai package (depends on base)
cd trustgraph-vertexai  
pip install -e .
cd ..

# Install flow package (for additional components)
cd trustgraph-flow
pip install -e .
cd ..

echo "Package installation complete!"
echo "Verify installation:"
#python -c "import trustgraph.model.text_completion.vertexai.llm; print('VertexAI import successful')"
