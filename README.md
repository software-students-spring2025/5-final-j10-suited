# 5-Final-J10-Suited

🔗 **Live Demo**: https://connectnyu-af7ih.ondigitalocean.app

> A Flask-based social “public board” for NYU students: join interest groups, post text + media, and have threaded, voteable discussions—powered by MongoDB, containerized with Docker, and deployed with GitHub Actions & DigitalOcean.

---

## Table of Contents

1. [Features](#features)  
2. [Tech Stack & Architecture](#tech-stack--architecture)  
3. [Quick Start](#quick-start)  
   - [Prerequisites](#prerequisites)  
   - [Clone & Configure](#clone--configure)  
   - [Run with Docker Compose](#run-with-docker-compose)  
   - [Run Locally (no Docker)](#run-locally-no-docker)  
4. [Environment Variables](#environment-variables)  
5. [Database Initialization](#database-initialization)  
6. [Running Tests](#running-tests)  
7. [CI/CD & Docker Images](#cicd--docker-images)  
8. [Team](#team)
9. [License](#license)  

---

## Features

- **NYU SSO Login** (placeholder for real integration)  
- **Group Management**: browse, create, and save interest groups  
- **Public Board**: create text & photo/video posts  
- **Nested Comments**: reply to any comment at any depth  
- **Voting System**: upvote/downvote posts and comments  

---

## Tech Stack & Architecture

- **Backend**: Python 3.13, Flask, Flask-Login, Flask-Mail, Flask-SocketIO  
- **Database**: MongoDB (official Docker image)  
- **Containerization**: Docker (separate `flask-app` & `mongo` services)  
- **Orchestration**: Docker Compose  
- **CI/CD**: GitHub Actions (build, test, Docker Hub publish, DigitalOcean deploy)  
- **Dependency Management**: Pipenv  
- **Testing**: PyTest  

---

## Quick Start

### Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/)  
- [Pipenv](https://pipenv.pypa.io/) (if running locally)  
- Python 3.13  

### Clone & Configure

```bash
git clone https://github.com/software-students-spring2025/5-final-j10-suited.git
cd 5-final-j10-suited
