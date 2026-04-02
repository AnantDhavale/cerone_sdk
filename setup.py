"""Setup configuration for Cerone Python SDK."""

import os
from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).parent
README = ROOT / "README.md"
os.chdir(ROOT)

setup(
    name="cerone",
    version="1.0.0",
    author="Anant Dhavale for Homer Semantics",
    author_email="info@homersemantics.com",
    description="Zero Trust Security for AI Agents",
    license="Proprietary - see LICENSE file",
    long_description=README.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/AnantDhavale/cerone_sdk",
    project_urls={
        "Documentation": "https://aztp.homersemantics.com/",
        "Bug Tracker": "https://github.com/AnantDhavale/cerone_sdk/issues",
        "Homepage": "https://aztp.homersemantics.com/",
    },
    packages=["cerone"],
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Security",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "async": [
            "aiohttp>=3.8.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    keywords="ai agent security zero-trust governance semantic-validation",
)
