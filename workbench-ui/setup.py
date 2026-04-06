
import setuptools
import os
import importlib

with open("README.md", "r") as fh:
    long_description = fh.read()

# Load a version number module
spec = importlib.util.spec_from_file_location(
    'version', 'workbench/version.py'
)
version_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version_module)

version = version_module.__version__

setuptools.setup(
    name="workbench-ui",
    version=version,
    author="trustgraph.ai",
    author_email="security@trustgraph.ai",
    description="Workbench for trustgraph.ai",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/trustgraph-ai/workbench-ui",
    packages=setuptools.find_namespace_packages(
        where='./',
    ),
    include_package_data=True,
    package_data={'': ["ui/**"]},
    classifiers=[ 
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=[
        "aiohttp",
        "prometheus-client",
        "websockets",
    ],
    scripts=[
        "scripts/service",
    ]
)

