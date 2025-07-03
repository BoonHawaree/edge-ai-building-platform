from setuptools import setup, find_packages

MAIN_MODULE = "agent"
agent_package = "llmbridge"

setup(
    name=agent_package + "agent",
    version="0.1",
    author="Your Name",
    author_email="your@email.com",
    install_requires=[
        "volttron",
        "fastapi",
        "uvicorn",
        "psycopg2-binary",  # For TimescaleDB/Postgres access
        # Add any other dependencies you need
    ],
    packages=find_packages(),
    entry_points={
        "setuptools.installation": [
            "eggsecutable = " + agent_package + "." + MAIN_MODULE + ":main",
        ]
    },
)