"""Compatibility shim for editable installs with older pip."""
from setuptools import setup, find_packages

setup(
    name="yadon-agents",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "yadon=yadon_agents.cli:main",
        ],
    },
)
