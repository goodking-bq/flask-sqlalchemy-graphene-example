from graphql_relay.node.node import from_global_id
from graphene_sqlalchemy.types import (
    sort_argument_for_object_type,
    default_connection_field_factory,
    get_global_registry,
    construct_fields,
    SQLAlchemyObjectType,
)
from graphene_sqlalchemy.converter import Dynamic
import sqlalchemy
from graphene.types.utils import yank_fields_from_attrs
import graphene


class SQLAlchemyInputObjectType(graphene.InputObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls, model=None, registry=None, only_fields=[], exclude_fields=[], **options
    ):
        # always pull 'id' out to a separate id argumentF
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
                obj_type=SQLAlchemyObjectTypes().get(model),
                model=model,
                registry=registry,
                only_fields=tuple(only_fields),
                exclude_fields=tuple(exclude_fields + autoexclude),
                connection_field_factory=default_connection_field_factory,
            ),
            _as=graphene.Field,
        )
        # Add all of the fields to the input type
        for key, value in sqla_fields.items():
            if not (isinstance(value, Dynamic) or hasattr(cls, key)):
                if key.endswith("_id"):
                    value = graphene.ID(description="Global Id")
                setattr(cls, key, value)

        super(SQLAlchemyInputObjectType, cls).__init_subclass_with_meta__(**options)


class DatabaseId(graphene.Interface):
    db_id = graphene.Int()


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
            if hasattr(model, "id"):
                model.db_id = model.id
            t = SQLAlchemyObjectType.create_type(
                name, model=model, interfaces=(graphene.relay.Node, DatabaseId)
            )
            self.all_types[name] = t
            return t
