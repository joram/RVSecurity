#!/usr/bin/env python

from setuptools import find_packages, setup

packages = [
    "uvicorn[standard]==0.15.0",
    "gunicorn==20.1.0",
    "fastapi==0.68.1",
    "requests==2.27.1",
    "aiofiles",
]

test_packages = [
    "mock==4.0.3",
    "pytest==6.2.1",
    "responses",
    "starlette",
    "mock",
]

linting_packages = [
    "pre-commit==2.9.3",
    "black==20.8b1",
    "flake8==3.8.4",
    "flake8-bugbear==20.1.4",
    "flake8-builtins==1.5.3",
    "flake8-comprehensions==3.2.3",
    "flake8-tidy-imports==4.2.1",
    "flake8-import-order==0.18.1",
]

setup(
    name="RVSecurity",
    version="1.0",
    description="A simple server for controlling an RV security system",
    author="John Oram",
    author_email="john@oram.ca",
    install_requires=packages,
    packages=find_packages(),
    extras_require={
        "dev": test_packages + linting_packages,
    },
)
