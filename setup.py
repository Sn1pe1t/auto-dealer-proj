"""
Setup configuration for AutoDealer Core library.
Install with: pip install -e .
Publish with: python setup.py sdist bdist_wheel
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="autodealer-core",
    version="0.1.0",
    author="AutoDealer Team",
    author_email="team@autodealer.dev",
    description="Core library for AutoDealer car dealership management system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Sn1pe1t/auto-dealer-proj",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Business",
        "Topic :: Office/Business",
    ],
    python_requires=">=3.7",
    include_package_data=True,
    package_data={
        'autodealer_core': ['schema.sql'],
    },
)
