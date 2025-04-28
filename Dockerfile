FROM python:3.13-slim

WORKDIR /app

COPY . .

COPY Pipfile Pipfile.lock ./
RUN pip install pipenv && pipenv install --deploy --ignore-pipfile

CMD [ "pipenv", "run", "python3", "app.py" ]
