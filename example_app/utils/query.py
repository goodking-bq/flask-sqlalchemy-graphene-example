from sqlalchemy import or_, not_
import graphene
from graphene_sqlalchemy.types import sort_argument_for_object_type
from graphene_sqlalchemy import SQLAlchemyConnectionField
from graphene.types.generic import GenericScalar
from .types import SQLAlchemyObjectTypes
from graphene.types.objecttype import ObjectTypeOptions
from collections import OrderedDict
from flask_sqlalchemy.model import DefaultMeta


def filter_query(query, model, filters):
    """make query 
    
    Arguments:
        query {query} -- sqlalchemyquery
        model {model} -- model
        filters {list} -- filter list,like [{key: a,val:a,op:aa}]
    
    Returns:
        query -- sqlalchemy query
    """
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
    """
    """
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
        """add default query 
        filters
        limit 
        offset
        """
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
    """
    CustomConnection

        default add total count for query list
    """

    class Meta:
        abstract = True

    total_count = graphene.Int()

    @staticmethod
    def resolve_total_count(root, info):
        return root.iterable.limit(None).offset(None).count()


def model_connection(model):
    connection = CustomConnection.create_type(
        model.__name__ + "Connection", node=SQLAlchemyObjectTypes().get(model)
    )
    return CustomConnectionField(
        connection,
        filters=GenericScalar(),
        limit=graphene.types.Int(),
        offset=graphene.types.Int(),
    )


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

