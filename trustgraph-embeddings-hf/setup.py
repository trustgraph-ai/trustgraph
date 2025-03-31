import setuptools
import os
import importlib

with open("README.md", "r") as fh:
    long_description = fh.read()

# Load a version number module
spec = importlib.util.spec_from_file_location(
    'version', 'trustgraph/embeddings_hf_version.py'
)
version_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version_module)

version = version_module.__version__

setuptools.setup(
    name="trustgraph-embeddings-hf",
    version=version,
    author="trustgraph.ai",
    author_email="security@trustgraph.ai",
    description="HuggingFace embeddings support for TrustGraph.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/trustgraph-ai/trustgraph",
    packages=setuptools.find_namespace_packages(
        where='./',
    ),
    classifiers=[ 
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    download_url = "https://github.com/trustgraph-ai/trustgraph/archive/refs/tags/v" + version + ".tar.gz",
    install_requires=[
        "trustgraph-base>=0.22,<0.23",
        "trustgraph-flow>=0.22,<0.23",
        "torch",
        "urllib3",
        "transformers",
        "sentence-transformers",
        "langchain",
        "langchain-core",
        "langchain-huggingface",
        "langchain-community",
        "huggingface-hub",
        "pulsar-client",
        "pyyaml",
        "prometheus-client",
    ],
    scripts=[
        "scripts/embeddings-hf",
    ]
)
