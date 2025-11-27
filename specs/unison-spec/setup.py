"""
Unison Specification Package
Shared contracts, schemas, and interfaces for all Unison services
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read version from __init__.py
version = "1.0.0"

setup(
    name="unison-spec",
    version=version,
    author="Unison Platform Team",
    author_email="team@project-unisonos.org",
    description="Shared specifications and contracts for Unison services",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/project-unisonos/unison-platform",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
    ],
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.5.0",
        "pydantic-settings>=2.0.0",
        "typing-extensions>=4.0.0",
        "python-dateutil>=2.8.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "mypy>=1.7.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "unison-spec=unison_spec.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "unison_spec": [
            "schemas/*.yaml",
            "topics.yaml",
            "contracts/*.py",
        ],
    },
    keywords=[
        "unison",
        "microservices",
        "contracts",
        "specifications",
        "api",
        "events",
        "distributed-systems",
    ],
    project_urls={
        "Bug Reports": "https://github.com/project-unisonos/unison-platform/issues",
        "Source": "https://github.com/project-unisonos/unison-platform",
        "Documentation": "https://docs.project-unisonos.org/",
    },
)
