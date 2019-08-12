# coding:utf-8
from __future__ import absolute_import, unicode_literals, annotations

from collections import OrderedDict

import graphene
import sqlalchemy
from flask_sqlalchemy.model import DefaultMeta
from graphene import relay
from graphene.types.generic import GenericScalar
from graphene.types.objecttype import ObjectTypeOptions
from graphene.types.utils import yank_fields_from_attrs
from graphene_sqlalchemy import SQLAlchemyConnectionField
from graphene_sqlalchemy.converter import (
    convert_sqlalchemy_type,
    convert_sqlalchemy_relationship,
    get_column_doc,
    is_column_nullable,
    Dynamic
)
from graphene_sqlalchemy.types import (
    sort_argument_for_object_type,
    default_connection_field_factory,
    get_global_registry,
    construct_fields,
    SQLAlchemyObjectType,
    convert_sqlalchemy_column,
    convert_sqlalchemy_composite,
    convert_sqlalchemy_hybrid_method,
)
from graphql_relay.node.node import from_global_id
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import or_, not_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.inspection import inspect as sqlalchemyinspect
from example_app.extensions import db
from sqlalchemy.orm.attributes import InstrumentedAttribute
from .types import SQLAlchemyObjectTypes, SQLAlchemyInputObjectType

__author__ = "golden"
__date__ = "2019/8/2"


def input_to_dictionary(input):
    """Method to convert Graphene inputs into dictionary"""
    dictionary = {}
    for key in input:
        # Convert GraphQL global id to database id
        if key[-2:] == "id":
            input[key] = from_global_id(input[key])[1]
        if isinstance(input[key], (dict,)):
            input[key] = input_to_dictionary(input[key])
        dictionary[key] = input[key]
    return dictionary


class SQLAlchemyMutationOptions(ObjectTypeOptions):
    model = None  # type: Model
    create = False  # type: Boolean
    delete = False  # type: Boolean
    arguments = None  # type: Dict[str, Argument]
    output = None  # type: Type[ObjectType]
    resolver = None  # type: Callable


class SQLAlchemyMutation(graphene.Mutation):
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model=None,
        create=False,
        delete=False,
        registry=None,
        arguments=None,
        only_fields=[],
        exclude_fields=[],
        **options
    ):
        meta = SQLAlchemyMutationOptions(cls)
        meta.create = create
        meta.model = model
        meta.delete = delete
        _out_name = "Edit"
        if meta.create is True:
            _out_name = "Create"
        if meta.delete is True:
            _out_name = "Delete"
        if arguments is None and not hasattr(cls, "Arguments"):
            arguments = {}
            # 不是创建
            if meta.create == False:
                arguments["id"] = graphene.ID(required=True)
            # 不是删除
            if meta.delete == False:
                input_meta = type(
                    "Meta",
                    (object,),
                    {"model": model, "exclude_fields": exclude_fields, "only_fields": only_fields},
                )
                input_type = type(
                    cls.__name__ + "Input", (SQLAlchemyInputObjectType,), {"Meta": input_meta}
                )

                arguments["input"] = graphene.Argument.mounted(input_type(required=True))
            else:
                _out_name = "Delete"
        cls.output = graphene.Field(lambda: SQLAlchemyObjectTypes().get(model), description="输出")
        cls.ok = graphene.Boolean(description="成功？")
        cls.message = graphene.String(description="更多信息")
        super(SQLAlchemyMutation, cls).__init_subclass_with_meta__(
            _meta=meta, arguments=arguments, **options
        )

    @classmethod
    def mutate(cls, self, info, **kwargs):
        kwargs = input_to_dictionary(kwargs)
        session = db.session

        meta = cls._meta

        if meta.create == True:
            model = meta.model()
            session.add(model)
        else:
            model = session.query(meta.model).filter(meta.model.id == kwargs["id"]).first()
            if not model:
                return cls(output=None, ok=False, message="要操作的数据不存在")
        if meta.delete == True:
            session.delete(model)
        else:

            def setModelAttributes(model, attrs):
                relationships = model.__mapper__.relationships
                for key, value in attrs.items():
                    if key in relationships:
                        if getattr(model, key) is None:
                            # instantiate class of the same type as the relationship target
                            setattr(model, key, relationships[key].mapper.entity())
                        setModelAttributes(getattr(model, key), value)
                    else:
                        setattr(model, key, value)

            setModelAttributes(model, kwargs["input"])

        if getattr(cls, "on_before_commit", None) is not None:
            cls.on_before_commit(self, model, **kwargs)
        try:
            session.commit()
        except SQLAlchemyError as e:
            return cls(output=None, ok=False, message="操作报错：%s" % e)
        if getattr(cls, "on_after_commit", None) is not None:
            cls.on_after_commit(self, model, **kwargs)
        return cls(output=model, ok=True, message="操作成功")

    @classmethod
    def Field(cls, *args, **kwargs):
        return graphene.Field(
            cls._meta.output, args=cls._meta.arguments, resolver=cls._meta.resolver
        )


def model_create(model):
    name = "%sCreateMutation" % model.__name__.capitalize()
    if globals().get(name):
        print("aaa")
    meta = type("Meta", (object,), {"model": model, "create": True, "delete": False})
    mutation = type(name, (SQLAlchemyMutation,), {"Meta": meta})
    return mutation


def model_update(model):
    name = "%sUpdateMutation" % model.__name__.capitalize()
    meta = type("Meta", (object,), {"model": model, "create": False, "delete": False})
    mutation = type(name, (SQLAlchemyMutation,), {"Meta": meta})
    return mutation


def model_delete(model):
    name = "%sDeleteMutation" % model.__name__.capitalize()
    meta = type("Meta", (object,), {"model": model, "create": False, "delete": True})
    mutation = type(name, (SQLAlchemyMutation,), {"Meta": meta})
    return mutation


class MutationObjectType(graphene.ObjectType):
    @classmethod
    def __init_subclass_with_meta__(cls, model_mudule, include_object=[], _meta=None, **options):
        if not _meta:
            _meta = ObjectTypeOptions(cls)
        fields = OrderedDict()
        include_object_names = list()
        for obj in include_object:
            action = "update"
            if obj._meta.create is True:
                action = "create"
            if obj._meta.delete is True:
                action = "delete"
            name = "%s%s" % (action, obj._meta.model.__name__)
            include_object_names.append(name)
            fields[name] = obj.Field()
        for model_name in dir(model_mudule):
            model_obj = getattr(model_mudule, model_name)
            if isinstance(model_obj, DefaultMeta):
                if "create%s" % model_name not in include_object_names:
                    fields.update({"create%s" % model_name: model_create(model_obj).Field()})
                if "update%s" % model_name not in include_object_names:
                    fields.update({"update%s" % model_name: model_update(model_obj).Field()})
                if "delete%s" % model_name not in include_object_names:
                    fields.update({"delete%s" % model_name: model_delete(model_obj).Field()})
        if _meta.fields:
            _meta.fields.update(fields)
        else:
            _meta.fields = fields
        return super(MutationObjectType, cls).__init_subclass_with_meta__(_meta=_meta, **options)
