from example_app.utils import (
    SQLAlchemyMutation,
    SQLAlchemyInputObjectType,
    input_to_dictionary,
)
from example_app.models import User, Role
from example_app.extensions import db
import graphene
from graphql_relay.node.node import from_global_id


class UserInputType(SQLAlchemyInputObjectType):
    class Meta:
        model = User

    roles = graphene.List(graphene.ID)  # roles


class UserCreateMutation(SQLAlchemyMutation):
    class Meta:
        model = User
        create = True
        delete = False

    class Arguments:
        input = UserInputType(required=True)

    @classmethod
    def mutate(cls, self, info, **kwargs):
        kwargs = input_to_dictionary(kwargs)
        data = kwargs.get("input")
        print(data)
        user = User()
        user.name = data.get("name", "defautltname")
        user.password = data.get("password")

        for _id in data.get("roles", []):
            rid = from_global_id(_id)[1]
            user.roles = [Role.query.get(rid) for i in data.get("roles")]
        db.session.add(user)
        db.session.commit()
        user = User.query.get(user.id)
        return cls(output=user, ok=True, message="操作成功")


class UserUpdateMutation(SQLAlchemyMutation):
    class Meta:
        model = User
        create = False
        delete = False

    class Arguments:
        input = UserInputType(required=True)
        id = graphene.ID(required=True)

    @classmethod
    def mutate(cls, self, info, **kwargs):
        kwargs = input_to_dictionary(kwargs)
        data = kwargs.get("input")
        print(data)
        user = User.query.get(kwargs.get("id"))
        user.name = data.get("name", "defautltname")
        user.password = data.get("password")

        for _id in data.get("roles"):
            rid = from_global_id(_id)[1]
            user.roles = [Role.query.get(rid) for i in data.get("roles")]
        db.session.add(user)
        db.session.commit()
        user = User.query.get(user.id)
        return cls(output=user, ok=True, message="操作成功")
