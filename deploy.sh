# !/usr/bin/bash
user=fuskar-owner
venv_name=fuskar
CWDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
services_dir="$CWDIR/services"
sytemd_path="/etc/systemd/system/"
nginx_conf="$CWDIR/nginx/fuskar"
sites_available="/etc/nginx/sites-available/"


echo "Starting Server Orchestration...\n"

echo "Creating new user...\n"
sudo adduser "$user"

echo "Installing aptitude packages...\n"
sudo apt install redis redis-server postgres nginx

echo "Installing virtualenvwrapper"
sudo python3 -H virtualenvwrapper

echo "Adding virtualenv variables to ~/.bashrc..\n"
echo 'source /usr/bin/virtualenvwrapper.sh;export WORKON_HOME=$HOME/envs;export PROJECT_HOME=$HOME/Projects;export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3;export VIRTUALENV_PYTHON=/usr/bin/python3' >> ~/.bashrc
. ~/.bashrc

echo "Making virtualenv and installing requirements"
mkvirtualenv "$venv_name"
workon "$venv_name"
pip install -r "$CWD/backend/requirements.txt"


echo "Setting up postgres database and user...\n"
sudo su postgres -c "psql -c \"CREATE ROLE fuskar with password 'fuskar';\""
sudo su postgres -c "psql -c \"CREATE DATABASE fuskardb with owner fuskar;\""
sudo su postgres -c "psql -c \"ALTER ROLE fuskar WITH LOGIN;\""


echo "Running migrations...\n"
workon "$venv_name"
python backend/manage.py migrate


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