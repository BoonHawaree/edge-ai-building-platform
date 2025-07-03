#! /usr/bin/env bash


if [[ -z /startup/setup-platform.py ]]; then
    echo "/startup/setup-platform.py does not exist.  The docker image must be corrupted"
    exit 1
fi

echo "Before platform setup, print environment."
printenv

#Check if the config file is already there and don't run setup-platform.py
# if it is. Otherwise, the startup errors out when setup-platform.py tries
# to write new certificates.
VOLTTRON_CONFIG=${VOLTTRON_HOME}"/config"

if [[ -e $VOLTTRON_CONFIG ]]
then
    echo "Container already initialized, skipping setup-platform.py"
else
    echo "Initializing container. Running setup-platform.py to setup the Volttron platform for the first and only time for this container..."

    # Only run pre_install_agents.py if SITE_ID is provided
    if [[ -n ${SITE_ID} ]]; then
        echo "SITE_ID provided: Installing agents for site $SITE_ID"
        python3 "/pre_install_agents.py" --site_id "$SITE_ID" --site_config_dir "/code/volttron/site_configs"
    else
        echo "No SITE_ID provided: Skipping agent installation"
    fi

    python3 /startup/setup-platform.py
    setup_return=$?
    if [[ $setup_return -ne 0 ]]; then
	    echo "error running setup-platform.py"
	    exit $setup_return
    fi
    echo "Setup of Volttron platform is complete."

fi

echo "Starting Volttron..."

# Now spin up the volttron platform
volttron -vv
volttron_retcode=$?
if [[ $volttron_retcode ]]; then
    echo "volttron error"
    exit $volttron_retcode
fi

# echo "Installing agents..."
# python3 /startup/install_agents.py --site_id=cp9 --site_config_dir=/site_configs
