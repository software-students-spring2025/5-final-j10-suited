# 5-Final-J10-Suited
![CI Build](https://github.com/software-students-spring2025/5-final-j10-suited/actions/workflows/build.yaml/badge.svg?event=pull_request)

**Live Demo**: https://connectnyu-af7ih.ondigitalocean.app

A Flask-based social network for members of the NYU community where users can join interest groups, post text + media, and have threaded, voteable discussions, with data is stored on MongoDB, containerized with Docker, and deployed using Digital Ocean.

---

## Team
* [Ava August](https://github.com/aaugust22)
* [Joel Kim](https://github.com/joel-d-kim)
* [Jack Wang](https://github.com/JackInTheBox314)
* [Tim Xu](https://github.com/timxu23)

---

## Features

- **Group Management**: browse, create, and save interest groups where users can talk to other users with similar needs or interests 
- **Public Board**: create text & photo/video posts  
- **Nested Comments**: reply to any comment at any depth  
- **Voting System**: upvote/downvote posts and comments  
- **Direct Messaging**: talk to other users one on one

---

## Subsystems
* MongoDB: [Docker Hub](https://hub.docker.com/_/mongo)
* Flask: [Docker Hub](https://hub.docker.com/repository/docker/timxu23/5-final-j10-suited-flask-app)

---

## Setup Instructions (local, dockerized)

Required software:

- install and run [docker desktop](https://www.docker.com/get-started)
- create a [dockerhub](https://hub.docker.com/signup) account

Use Docker Compose to boot up both the mongodb database and the flask app using one command:

- Navigate to app directory which contains `Dockerfile`
- open Docker
- `docker compose up --build` ... add -d to run in detached/background mode.
- Ctrl + C then `docker compose down` when done to stop containers

If port number already use, select different port for `flask-app` or `mongodb` by changing their values in `docker-compose.yml`

View the app in browser:

- open `http://localhost:5001` in preferred web browser (or whatever port number used for host)

_Note that if any files were edited, container must be stopped then restarted_
