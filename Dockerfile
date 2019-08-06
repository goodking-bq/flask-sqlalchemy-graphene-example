FROM python:3.7
MAINTAINER golden "https://github.com/goodking-bq"
RUN git clone https://github.com/goodking-bq/flask-sqlalchemy-graphene-example.git /opt/flask-sqlalchemy-graphene-example && pip install pipenv
WORKDIR /opt/flask-sqlalchemy-graphene-example
ENV FLASK_APP /opt/flask-sqlalchemy-graphene-example/run.py
ENV HOST 0.0.0.0
ENV PORT 5000
RUN pipenv install
RUN pipenv run flask db init &&pipenv run flask db migrate &&pipenv run flask db upgrade
ENTRYPOINT ["flask","run"]
CMD ["--host","$HOST","--port","$PORT"]