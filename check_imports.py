#!/usr/bin/env python3
"""
Check if TrustGraph imports work correctly for testing
"""

import sys
import traceback

def check_import(module_name, description):
    """Try to import a module and report the result"""
    try:
        __import__(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_name}")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        print(f"❌ {description}: {module_name}")
        print(f"   Unexpected error: {e}")
        return False

def main():
    print("Checking TrustGraph imports for testing...")
    print("=" * 50)
    
    imports_to_check = [
        ("trustgraph", "Base trustgraph package"),
        ("trustgraph.base", "Base classes"),
        ("trustgraph.base.llm_service", "LLM service base class"),
        ("trustgraph.schema", "Schema definitions"),
        ("trustgraph.exceptions", "Exception classes"),
        ("trustgraph.model", "Model package"),
        ("trustgraph.model.text_completion", "Text completion package"),
        ("trustgraph.model.text_completion.vertexai", "VertexAI package"),
    ]
    
    success_count = 0
    total_count = len(imports_to_check)
    
    for module_name, description in imports_to_check:
        if check_import(module_name, description):
            success_count += 1
        print()
    
    print("=" * 50)
    print(f"Import Check Results: {success_count}/{total_count} successful")
    
    if success_count == total_count:
        print("✅ All imports successful! Tests should work.")
    else:
        print("❌ Some imports failed. Please install missing packages.")
        print("\nTo fix, run:")
        print("  ./install_packages.sh")
        print("or install packages manually:")
        print("  cd trustgraph-base && pip install -e . && cd ..")
        print("  cd trustgraph-vertexai && pip install -e . && cd ..")
        print("  cd trustgraph-flow && pip install -e . && cd ..")
    
    # Test the specific import used in the test
    print("\n" + "=" * 50)
    print("Testing specific import from test file...")
    try:
        from trustgraph.model.text_completion.vertexai.llm import Processor
        from trustgraph.schema import TextCompletionRequest, TextCompletionResponse, Error
        from trustgraph.base import LlmResult
        print("✅ Test imports successful!")
    except Exception as e:
        print(f"❌ Test imports failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
