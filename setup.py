"""Setup configuration for PolarionMock."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="polarion-mock",
    version="0.1.0",
    author="PolarionMock Team",
    author_email="",
    description="A comprehensive mock and testing framework for Polarion ALM",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/polarion-mock",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "Flask>=3.0.0",
        "Flask-CORS>=4.0.0",
        "Flask-SocketIO>=5.3.5",
        "pytest>=7.4.3",
        "requests>=2.31.0",
        "pydantic>=2.5.2",
        "python-dotenv>=1.0.0",
        "click>=8.1.7",
    ],
    extras_require={
        "dev": [
            "black>=23.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "pre-commit>=3.6.0",
        ],
        "test": [
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "pytest-html>=4.1.1",
            "pytest-json-report>=1.5.0",
            "pytest-benchmark>=4.0.0",
            "pytest-xdist>=3.5.0",
            "pytest-timeout>=2.2.0",
            "responses>=0.24.1",
            "faker>=20.1.0",
        ],
        "dashboard": [
            "dash>=2.14.1",
            "plotly>=5.18.0",
            "dash-bootstrap-components>=1.5.0",
        ],
        "docs": [
            "sphinx>=7.2.6",
            "sphinx-rtd-theme>=2.0.0",
            "myst-parser>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "polarion-mock=src.mock.cli:main",
            "polarion-test=tests.cli:main",
        ],
    },
)