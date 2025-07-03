#!/bin/bash

# Setup variables
# Check if a custom working directory is provided as an argument
if [ "$1" != "" ]; then
    workdir=$1
else
    workdir="/home/alto"
fi

echo "Working directory set to $workdir"
echo "WORKDIR=$workdir" | sudo tee /etc/default/volttron > /dev/null

mkdir -p $workdir
alto_os_lib_path="$workdir/alto_os/libraries"

# Check volttron version, if version is 8.2 auto use "releases/8.2", else input from terminal
read -p "Volttron version is 8.2? [y/n]: " volttron_version_check
if [[ $volttron_version_check =~ ^[Yy] ]]; then
    echo -e "Volttron version is 8.2"
    volttron_version="releases/8.2"
elif [[ $volttron_version_check =~ ^[Nn] ]]; then
    echo -e "Please input volttron version (e.g. 8.x, 8.2, main)"
    read -p "\nVolttron version: " version
    # check version is numeric, else exit
    if [[ $version =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo -e "\nVolttron version is $version"
        volttron_version="$version"
    elif [[ $version =~ ^[Mm][Aa][Ii][Nn]$ ]]; then
        echo -e "\nVolttron version is main"
        volttron_version="main"
    else
        echo -e "\nInvalid input, please try again."
        exit 1
    fi
else
    echo -e "\nInvalid input, please try again."
    exit 1
fi

# Setup Volttron requirement application
sudo apt-get install -y build-essential libffi-dev python3-dev python3-venv openssl libssl-dev libevent-dev git

# Clone Volttron
if [ -d $workdir/volttron]; then
    echo -e "\nVolttron already exists in the path ~/volttron"
else
    # Install Volttron requirements application
    echo "Cloning Volttron into working directory"
    git clone https://github.com/VOLTTRON/volttron.git --branch $volttron_version $workdir/volttron

    echo -e "Bootstrapping Volttron..."
    /bin/python3 $workdir/volttron/bootstrap.py
fi

# Start Volttron Systemd service
sudo cp $workdir/alto_os/Tools/volttron-start-systemd /etc/systemd/system/volttron.service
sudo chmod +x /etc/systemd/system/volttron.service
sudo systemctl daemon-reload
sudo systemctl enable volttron.service
sudo systemctl start volttron.service
sudo systemctl restart volttron.service
sleep 5

# Activate Volttron virtual environment
source $workdir/volttron/env/bin/activate

# Install python packages in the requirements.txt
$workdir/volttron/env/bin/pip install -r $workdir/alto_os/requirements.txt

# altolib
cd $alto_os_lib_path/altolib
echo "Installing altolib..."
python setup.py install

# altoutils
cd $alto_os_lib_path/altoutils
echo "Installing altoutils..."
python setup.py install

# irgen
cd $alto_os_lib_path/irgen
echo "Installing irgen..."
python setup.py install

# python-broadlink
cd $alto_os_lib_path/python-broadlink
echo "Installing python-broadlink..."
python setup.py install

# back to root path
echo -e "Done installing Alto OS"
cd $workdir/alto_os
