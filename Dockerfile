FROM python:3.13-slim

WORKDIR /app

COPY Pipfile Pipfile.lock ./

RUN pip install --upgrade pip \
 && pip install pipenv \
 && pipenv install --deploy --system --ignore-pipfile

COPY . .

CMD [ "python", "app.py" ]
