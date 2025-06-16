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
        "trustgraph-base>=1.0,<1.1",
        "requests",
        "pulsar-client",
        "aiohttp",
        "rdflib",
        "tabulate",
        "msgpack",
        "websockets",
    ],
    scripts=[
        "scripts/tg-add-library-document",
        "scripts/tg-delete-flow-class",
        "scripts/tg-delete-kg-core",
        "scripts/tg-dump-msgpack",
        "scripts/tg-get-flow-class",
        "scripts/tg-get-kg-core",
        "scripts/tg-graph-to-turtle",
        "scripts/tg-init-trustgraph",
        "scripts/tg-invoke-agent",
        "scripts/tg-invoke-document-rag",
        "scripts/tg-invoke-graph-rag",
        "scripts/tg-invoke-llm",
        "scripts/tg-invoke-prompt",
        "scripts/tg-load-doc-embeds",
        "scripts/tg-load-kg-core",
        "scripts/tg-load-pdf",
        "scripts/tg-load-sample-documents",
        "scripts/tg-load-text",
        "scripts/tg-load-turtle",
        "scripts/tg-put-flow-class",
        "scripts/tg-put-kg-core",
        "scripts/tg-remove-library-document",
        "scripts/tg-save-doc-embeds",
        "scripts/tg-set-prompt",
        "scripts/tg-set-token-costs",
        "scripts/tg-show-config",
        "scripts/tg-show-flow-classes",
        "scripts/tg-show-flow-state",
        "scripts/tg-show-flows",
        "scripts/tg-show-graph",
        "scripts/tg-show-kg-cores",
        "scripts/tg-show-library-documents",
        "scripts/tg-show-library-processing",
        "scripts/tg-show-processor-state",
        "scripts/tg-show-prompts",
        "scripts/tg-show-token-costs",
        "scripts/tg-show-token-rate",
        "scripts/tg-show-tools",
        "scripts/tg-start-flow",
        "scripts/tg-unload-kg-core",
        "scripts/tg-start-library-processing",
        "scripts/tg-stop-flow",
        "scripts/tg-stop-library-processing",
    ]
)
