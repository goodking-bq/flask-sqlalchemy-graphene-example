FROM alpine/git as build
MAINTAINER golden "https://github.com/goodking-bq"
RUN git clone https://github.com/goodking-bq/flask-sqlalchemy-graphene-example.git /opt/flask-sqlalchemy-graphene-example &&rm -rf /opt/flask-sqlalchemy-graphene-example/.git
from python:3.7-alpine
WORKDIR /opt/flask-sqlalchemy-graphene-example
RUN pip install -r requirements.txt
RUN mkdir /data
ENV FLASK_APP /opt/flask-sqlalchemy-graphene-example/run.py
ENV HOST 0.0.0.0
ENV PORT 5000
RUN flask db init &&flask db migrate &&flask db upgrade && rm -rf migrations
CMD flask run --host=$HOST --port=$PORT