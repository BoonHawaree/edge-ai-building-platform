from setuptools import setup, find_packages

MAIN_MODULE = "agent"

# Find the agent package that contains the main module
packages = find_packages(".")
agent_package = "timescaledb"

# Find the version number from the main module
agent_module = agent_package + "." + MAIN_MODULE
_temp = __import__(agent_module, globals(), locals(), ["__version__"], 0)
__version__ = _temp.__version__

# Setup
setup(
    name=agent_package + "agent",
    version=__version__,
    author="ZayarNaing",
    author_email="zayarnaing.ai@gmail.com",
    install_requires=["volttron"],
    packages=packages,
    package_data={
        'timescaledb': [
            'sql/create_tables/*.sql',
            'sql/continuous_aggregations/*.sql'
        ]
    },
    entry_points={
        "setuptools.installation": [
            "eggsecutable = " + agent_module + ":main",
        ]
    },
)
