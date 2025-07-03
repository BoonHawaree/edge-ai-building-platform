from setuptools import setup, find_packages

MAIN_MODULE = "agent"
agent_package = "powermetersim"

setup(
    name=agent_package + "agent",
    version="0.1",
    author="Your Name",
    author_email="your@email.com",
    install_requires=["volttron"],
    packages=find_packages(),
    entry_points={
        "setuptools.installation": [
            "eggsecutable = " + agent_package + "." + MAIN_MODULE + ":main",
        ]
    },
)