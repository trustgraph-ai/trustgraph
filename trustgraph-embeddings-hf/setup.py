import setuptools
import os

with open("README.md", "r") as fh:
    long_description = fh.read()

version = "0.11.6"

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
#         include=['trustgraph.core']
    ),
    classifiers=[ 
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    download_url = "https://github.com/trustgraph-ai/trustgraph/archive/refs/tags/v" + version + ".tar.gz",
    install_requires=[
        "trustgraph-core",
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
