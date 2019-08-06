from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from example_app.extensions import *
from .scheme import schema
from flask_graphql import GraphQLView

app = Flask(__name__)

app.config.update(
    {
        "SQLALCHEMY_DATABASE_URI": "sqlite:////data/example.db",
        "SQLALCHEMY_TRACK_MODIFICATIONS": True,
        "DEBUG": True,
    }
)
db.init_app(app)

migrate.init_app(app, db)
# 视图
app.add_url_rule(
    "/graphql", view_func=GraphQLView.as_view("graphql", schema=schema, graphiql=True)
)

