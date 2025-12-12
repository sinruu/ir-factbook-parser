"""
IR FactBook Parser 설치 스크립트
"""

from setuptools import setup, find_packages
from pathlib import Path

# README 읽기
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="ir-factbook-parser",
    version="0.1.0",
    description="4대 금융지주 IR FactBook 정규화 파서",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/sinruu/ir-factbook-parser",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "": ["config/*.yaml"],
    },
    python_requires=">=3.9",
    install_requires=[
        "openpyxl>=3.1.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "pyyaml>=6.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "factbook-parser=src.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial",
    ],
)
