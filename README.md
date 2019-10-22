# Fuskar

This is a facial recognition application built to be deployed on an NVIDIA Jetson Nano
It combines the similarity comparison of the FaceNet Model trained on a Siamese network into a django API served to a VueJS frontend

## Development

### Backend

The API was built using django and face_recognition

```bash
    # create virtualenv
    mkvirtualenv fuskar
    # install requirements
    pip install -r backend/requirements.txt
    # create postgres database
    sudo su postgres -c "psql -c \"CREATE ROLE fuskar with password 'fuskar';\""
    sudo su postgres -c "psql -c \"CREATE DATABASE fuskardb with owner fuskar;\""
    sudo su postgres -c "psql -c \"ALTER ROLE fuskar WITH LOGIN;\""
    # change directory
    cd backend
    # run migrations
    python manage.py migrate
    # start server
    python manage.py runserver
```

### Frontend

The front end was built using nuxtjs, a progressive vuejs framework that supports server side rendering. Code [here](https://github.com/abdulqudus001/student-attendance)

## Build Setup

``` bash
# install dependencies
$ yarn install

# serve with hot reload at localhost:3000
$ yarn dev

# build for production and launch server
$ yarn build
$ yarn start

# generate static project
$ yarn generate
```

For detailed explanation on how things work, check out [Nuxt.js docs](https://nuxtjs.org).
