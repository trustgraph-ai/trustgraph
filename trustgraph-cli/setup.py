import setuptools
import os
import importlib

with open("README.md", "r") as fh:
    long_description = fh.read()

# Load a version number module
spec = importlib.util.spec_from_file_location(
    'version', 'trustgraph/cli_version.py'
)
version_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version_module)

version = version_module.__version__

setuptools.setup(
    name="trustgraph-cli",
    version=version,
    author="trustgraph.ai",
    author_email="security@trustgraph.ai",
    description="TrustGraph provides a means to run a pipeline of flexible AI processing components in a flexible means to achieve a processing pipeline.",
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
        "trustgraph-base>=0.16,<0.17",
        "requests",
        "pulsar-client",
        "rdflib",
        "tabulate",
    ],
    scripts=[
        "scripts/tg-graph-show",
        "scripts/tg-graph-to-turtle",
        "scripts/tg-init-pulsar-manager",
        "scripts/tg-load-pdf",
        "scripts/tg-load-text",
        "scripts/tg-load-turtle",
        "scripts/tg-query-document-rag",
        "scripts/tg-query-graph-rag",
        "scripts/tg-init-pulsar",
        "scripts/tg-processor-state",
        "scripts/tg-invoke-agent",
        "scripts/tg-invoke-prompt",
        "scripts/tg-invoke-llm",
    ]
)
