from setuptools import setup, find_packages

setup(
    name="ai-autopilot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "python-dotenv",
        "pydantic",
        "langgraph",
        "google-generativeai"
    ],
) 