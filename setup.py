from setuptools import find_packages, setup

setup(
    name="kalyx",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115,<1.0",
        "uvicorn>=0.30,<1.0",
        "pydantic>=2.7,<3.0",
    ],
    entry_points={
        "console_scripts": [
            "kalyx=kalyx.cli:main",
            "kalyx-api=kalyx.api.app:run",
        ],
    },
)
