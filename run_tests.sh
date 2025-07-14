#!/bin/bash
# Test runner script for TrustGraph

echo "TrustGraph Test Runner"
echo "===================="

# Check if we're in the right directory
if [ ! -f "install_packages.sh" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "   Expected files: install_packages.sh, check_imports.py"
    exit 1
fi

# Step 1: Check current imports
echo "Step 1: Checking current imports..."
python check_imports.py

# Step 2: Install packages if needed
echo ""
echo "Step 2: Installing TrustGraph packages..."
echo "This may take a moment..."
./install_packages.sh

# Step 3: Check imports again
echo ""
echo "Step 3: Verifying imports after installation..."
python check_imports.py

# Step 4: Install test dependencies
echo ""
echo "Step 4: Installing test dependencies..."
cd tests/
pip install -r requirements.txt
cd ..

# Step 5: Run the tests
echo ""
echo "Step 5: Running VertexAI tests..."
echo "Command: pytest tests/unit/test_text_completion/test_vertexai_processor.py -v"
echo ""

# Set Python path just in case
export PYTHONPATH=$PWD:$PYTHONPATH

pytest tests/unit/test_text_completion/test_vertexai_processor.py -v

echo ""
echo "Test run complete!"