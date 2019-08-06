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
    get_column_doc,
    is_column_nullable,
    Dynamic,
)
from graphene_sqlalchemy.types import construct_fields, SQLAlchemyObjectType
from graphene_sqlalchemy.types import (
    sort_argument_for_object_type,
    default_connection_field_factory,
    get_global_registry,
    construct_fields,
    SQLAlchemyObjectType,
)
from graphql_relay.node.node import from_global_id
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import or_, not_

from example_app.extensions import db

__author__ = "golden"
__date__ = "2019/8/2"


def input_to_dictionary(input):
    """Method to convert Graphene inputs into dictionary"""
    dictionary = {}
    for key in input:
        # Convert GraphQL global id to database id
        if key[-2:] == "id":
            input[key] = from_global_id(input[key])[1]
        dictionary[key] = input[key]
    return dictionary


def filter_query(query, model, filters):
    for _filter in filters:
        conditions = []
        if isinstance(_filter, (list,)):
            for __filter in _filter:
                conditions = construct_conditions(conditions, __filter, model)
            condition = or_(*conditions)
            query = query.filter(condition)
        if isinstance(_filter, (dict,)):
            conditions = construct_conditions(conditions, _filter, model)
            query = query.filter(*conditions)
    return query


def construct_conditions(conditions, _filter, model):
    c = getattr(model, _filter.get("key"))
    v = _filter.get("val")
    op = _filter.get("op")
    if not c or not op or not v:
        pass
    if op == "==":
        conditions.append(c == v)
    if op == "!=":
        conditions.append(c != v)
    if op == "<=":
        conditions.append(c <= v)
    if op == ">=":
        conditions.append(c >= v)
    if op == ">":
        conditions.append(c > v)
    if op == "<":
        conditions.append(c < v)
    if op == "starts":
        conditions.append(c.ilike(v + "%"))
    if op == "ends":
        conditions.append(c.ilike("%" + v))
    if op == "contains":
        conditions.append(c.contains(v))
    if op == "in":
        conditions.append(c.in_(v))
    if op == "notin":
        conditions.append(not_(c.in_(v)))
    return conditions


class CustomConnectionField(SQLAlchemyConnectionField):
    def __init__(self, connection, *args, **kwargs):
        model = connection.Edge.node._type._meta.model
        if "filters" not in kwargs:
            kwargs.setdefault("filters", sort_argument_for_object_type(model))
        elif "filters" in kwargs and kwargs["filters"] is None:
            del kwargs["filters"]
        if "limit" not in kwargs:
            kwargs.setdefault("limit", sort_argument_for_object_type(model))
        elif "limit" in kwargs and kwargs["limit"] is None:
            del kwargs["limit"]
        if "offset" not in kwargs:
            kwargs.setdefault("offset", sort_argument_for_object_type(model))
        elif "offset" in kwargs and kwargs["offset"] is None:
            del kwargs["offset"]
        super(CustomConnectionField, self).__init__(connection, *args, **kwargs)

    @classmethod
    def get_query(cls, model, info, **args):
        query = super(CustomConnectionField, cls).get_query(model, info, **args)
        if args.get("filters"):
            query = filter_query(query, model, args["filters"])
        if "limit" in args:
            query = query.limit(args["limit"])
        if "offset" in args:
            query = query.offset(args["offset"])
        return query


class CustomConnection(graphene.relay.Connection):
    class Meta:
        abstract = True

    total_count = graphene.Int()

    @staticmethod
    def resolve_total_count(root, info):
        return root.iterable.limit(None).offset(None).count()


@convert_sqlalchemy_type.register(ARRAY)
def convert_column_to_string(type, column, registry=None):
    return graphene.List(
        of_type=graphene.String,
        description=get_column_doc(column),
        required=not (is_column_nullable(column)),
    )


@convert_sqlalchemy_type.register(JSONB)
def convert_column_to_json(type, column, registry=None):
    return graphene.JSONString(
        description=get_column_doc(column), required=not (is_column_nullable(column))
    )


class SQLAlchemyInputObjectType(graphene.InputObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model=None,
        registry=None,
        skip_registry=False,
        only_fields=[],
        exclude_fields=[],
        connection=None,
        use_connection=None,
        interfaces=(),
        id=None,
        **options
    ):
        # always pull 'id' out to a separate id argument
        exclude_fields.append("id")
        if not registry:
            registry = get_global_registry()
        autoexclude = []

        # always pull ids out to a separate argument
        for col in sqlalchemy.inspect(model).columns:
            if (col.primary_key and col.autoincrement) or (
                isinstance(col.type, sqlalchemy.types.TIMESTAMP)
                and col.server_default is not None
            ):
                autoexclude.append(col.name)
        sqla_fields = yank_fields_from_attrs(
            construct_fields(
                SQLAlchemyObjectTypes().get(model),
                model,
                registry,
                tuple(only_fields),
                tuple(exclude_fields + autoexclude),
                default_connection_field_factory,
            ),
            _as=graphene.Field,
        )
        # Add all of the fields to the input type
        for key, value in sqla_fields.items():
            if not (isinstance(value, Dynamic) or hasattr(cls, key)):
                setattr(cls, key, value)

        super(SQLAlchemyInputObjectType, cls).__init_subclass_with_meta__(**options)


class SQLAlchemyObjectTypes(object):
    """SQLAlchemyObjectType 不能创建多次，要不然会报错，这个类解决这个问题, 这个类是单例模式"""

    all_types = {}

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            orig = super(SQLAlchemyObjectTypes, cls)
            cls._instance = orig.__new__(cls, *args, **kwargs)
        return cls._instance

    def get(self, model):
        name = model.__name__.capitalize() + "OutputType"
        if name in self.all_types:
            return self.all_types.get(name)
        else:
            t = SQLAlchemyObjectType.create_type(
                name, model=model, interfaces=(graphene.relay.Node,)
            )
            self.all_types[name] = t
            return t


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

        if arguments is None and not hasattr(cls, "Arguments"):
            arguments = {}
            # 不是创建
            if meta.create == False:
                arguments["id"] = graphene.ID(required=True)
            else:
                _out_name = "Create"
            # 不是删除
            if meta.delete == False:
                input_meta = type(
                    "Meta",
                    (object,),
                    {
                        "model": model,
                        "exclude_fields": exclude_fields,
                        "only_fields": only_fields,
                    },
                )
                input_type = type(
                    cls.__name__ + "Input",
                    (SQLAlchemyInputObjectType,),
                    {"Meta": input_meta},
                )

                arguments["input"] = graphene.Argument.mounted(
                    input_type(required=True)
                )
            else:
                _out_name = "Delete"
        cls.output = graphene.Field(
            lambda: SQLAlchemyObjectTypes().get(model), description="输出"
        )
        cls.ok = graphene.Boolean(description="成功？")
        cls.message = graphene.String(description="更多信息")
        super(SQLAlchemyMutation, cls).__init_subclass_with_meta__(
            _meta=meta, arguments=arguments, **options
        )

    @classmethod
    def mutate(cls, self, info, **kwargs):
        session = db.session

        meta = cls._meta

        if meta.create == True:
            model = meta.model()
            session.add(model)
        else:
            model = (
                session.query(meta.model).filter(meta.model.id == kwargs["id"]).first()
            )
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


def model_connection(model):
    connection = relay.Connection.create_type(
        model.__name__ + "Connection", node=SQLAlchemyObjectTypes().get(model)
    )
    return CustomConnectionField(
        connection,
        filters=GenericScalar(),
        limit=graphene.types.Int(),
        offset=graphene.types.Int(),
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


class QueryObjectType(graphene.ObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls, model_mudule, exclude_models=[], _meta=None, **options
    ):
        if not _meta:
            _meta = ObjectTypeOptions(cls)
        fields = OrderedDict()
        fields["node"] = graphene.relay.Node.Field()
        for model_name in dir(model_mudule):
            model_obj = getattr(model_mudule, model_name)
            if isinstance(model_obj, DefaultMeta):
                fields.update(
                    {
                        model_name.lower(): graphene.relay.Node.Field(
                            SQLAlchemyObjectTypes().get(model_obj)
                        ),
                        "%s_list" % model_name.lower(): model_connection(model_obj),
                    }
                )
        if _meta.fields:
            _meta.fields.update(fields)
        else:
            _meta.fields = fields
        return super(QueryObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, **options
        )


class MutationObjectType(graphene.ObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls, model_mudule, exclude_models=[], _meta=None, **options
    ):
        if not _meta:
            _meta = ObjectTypeOptions(cls)
        fields = OrderedDict()
        for model_name in dir(model_mudule):
            model_obj = getattr(model_mudule, model_name)
            if isinstance(model_obj, DefaultMeta):
                fields.update(
                    {
                        "create%s" % model_name: model_create(model_obj).Field(),
                        "update%s" % model_name: model_update(model_obj).Field(),
                        "delete%s" % model_name: model_delete(model_obj).Field(),
                    }
                )
        if _meta.fields:
            _meta.fields.update(fields)
        else:
            _meta.fields = fields
        return super(MutationObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, **options
        )

