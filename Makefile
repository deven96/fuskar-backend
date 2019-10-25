dev:
	@python backend/manage.py migrate
	@python backend/manage.py runserver

shell:
	@python backend/manage.py shell

reset-postgres:
	@sudo su postgres -c "psql -c \"DROP DATABASE fuskardb;\""
	@sudo su postgres -c "psql -c \"CREATE DATABASE fuskardb with owner fuskar;\"" && echo "FUSKAR >>> cleared database and created new"

celery:
	# start celery message broker a.k.a redis
	@gnome-terminal -e redis-server
	# start celery
	@cd backend && celery -A backend worker -n self_killing --loglevel=INFO

purge-tasks:
	@cd backend && celery -A backend purge

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
