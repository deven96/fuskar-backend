ngrok: ngrok-server localhost

dev:
	@python backend/manage.py migrate
	@python backend/manage.py runserver 192.168.122.1:8000

localhost:
	@python backend/manage.py runserver

ngrok-server:
	@ngrok http 8000

shell:
	@python backend/manage.py shell

reset-postgres:
	@sudo su postgres -c "psql -c \"DROP DATABASE fuskardb;\""
	@sudo su postgres -c "psql -c \"CREATE DATABASE fuskardb with owner fuskar;\"" && echo "FUSKAR >>> cleared database and created new"

consumer:
	@gnome-terminal -e redis-server
	@cd backend && ./manage.py run_huey --flush-locks

purge-tasks:
	@cd backend && celery -A backend purge -f

requirements:
	sudo apt-get install redis-server postgres	
	# create postgres database
	@echo "FUSKAR >>> Setting up postgres db" 
	@sudo su postgres -c "psql -c \"CREATE ROLE fuskar with password 'fuskar';\""
	@sudo su postgres -c "psql -c \"CREATE DATABASE fuskardb with owner fuskar;\""
	@sudo su postgres -c "psql -c \"ALTER ROLE fuskar WITH LOGIN;\""
	workon fuskar
	@echo "FUSKAR >>> Installing python requirements" 
	@pip install -r backend/requirements.txt
	@echo "FUSKAR >>> Python requirements complete"
