from example_app import models
from example_app.utils import MutationObjectType, QueryObjectType
import graphene
from .schemes import UserCreateMutation, UserUpdateMutation


class Query(QueryObjectType):
    class Meta:
        model_mudule = models


class Mutation(MutationObjectType):
    class Meta:
        model_mudule = models
        include_object = [UserCreateMutation, UserUpdateMutation]


schema = graphene.Schema(query=Query, mutation=Mutation)
