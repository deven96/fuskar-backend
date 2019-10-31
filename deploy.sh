# !/usr/bin/bash
user=fuskar-owner
CWDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
services_dir="$CWDIR/services"
sytemd_path="/etc/systemd/system/"
nginx_conf="$CWDIR/nginx/fuskar"
sites_available="/etc/nginx/sites-available/"


echo "Starting Server Orchestration"

echo "Creating new user "
sudo adduser fuskar-owner

echo "Installing aptitude packages"
sudo apt install redis redis-server postgres nginx

echo "Installing virtualenvwrapper"
sudo python3 -H virtualenvwrapper

echo "Adding virtualenv variables to .bashrc"
echo 'source /usr/bin/virtualenvwrapper.sh;export WORKON_HOME=$HOME/envs;export PROJECT_HOME=$HOME/Projects;export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3;export VIRTUALENV_PYTHON=/usr/bin/python3' >> ~/.bashrc
. ~/.bashrc

echo "Making virtualenv and installing requirements"
mkvirtualenv fuskar
workon fuskar
pip install -r "$CWD/backend/requirements.txt"



for entry in "$services_dir"/*
do
  # get file base name
  filename="$(basename $entry)"
  echo "Copying service file "$filename" to systemd folder"
  sudo cp "$entry" "$sytemd_path"
done


echo "Copying nginx config "$nginx_conf" to sites-available"
sudo cp "$nginx_conf" "$sites_available"

# TODO: start up all services and check statuses