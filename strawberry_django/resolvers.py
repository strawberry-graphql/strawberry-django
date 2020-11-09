from typing import List, Optional, cast
import strawberry
from . import utils
from .types import generate_model_type
from .permissions import permission_class_wrapper
from django.core import exceptions


class ModelResolverMixin:
    field_permission_classes = None
    permission_classes = None
    fields = None
    exclude = None
    readonly_fields = None

    def __init__(self, info, root):
        self.info = info
        self.root = root
        self.request = None
        if info.context:
            self.request = info.context.get('request')

    def get_model(self):
        return self.model

    def get_queryset(self):
        model = self.get_model()
        return model.objects.all()

    def get_queryset_filtered(self, filters):
        qs = self.get_queryset()
        if not filters:
            return qs
        filters, excludes = utils.split_filters(filters)
        if filters:
            qs = qs.filter(**filters)
        if excludes:
            qs = qs.exclude(**excludes)
        return qs

    def list(self, **filters):
        qs = self.get_queryset_filtered(**filters)
        return qs

    def get(self, id):
        qs = self.get_queryset()
        return qs.get(id=id)

    def create(self, data):
        model = self.get_model()
        instance = model(**data)
        instance.save()
        return instance

    def update(self, data, **filters):
        qs = self.get_queryset_filtered(**filters)
        qs.update(**data)
        return qs

    def delete(self, **filters):
        qs = self.get_queryset_filtered(**filters)
        items = list(qs)
        qs.delete()
        return items


def get_permission_classes(cls, permission_codename):
    if not cls.permission_classes:
        return None
    permission_classes = [
        permission_class_wrapper(permission_class, cls.model, permission_codename)
            for permission_class in cls.permission_classes
    ]
    return permission_classes


class ModelFieldMixin:
    @classmethod
    def get_field(cls):
        permission_classes = get_permission_classes(cls, 'view')

        @strawberry.field(permission_classes=permission_classes)
        def get_field(info, root, id: strawberry.ID) -> cls.output_type:
            instance = cls(info, root)
            return instance.get(id)

        return get_field

    @classmethod
    def list_field(cls):
        permission_classes = get_permission_classes(cls, 'view')

        @strawberry.field(permission_classes=permission_classes)
        def list_field(info, root,
                filters: Optional[List[str]] = None) -> List[cls.output_type]:
            instance = cls(info, root)
            return instance.list(filters=filters)

        return list_field

    @classmethod
    def query_fields(cls):
        return cls.get_field(), cls.list_field()


class ModelMutationMixin:
    @classmethod
    def create_mutation(cls):
        permission_classes = get_permission_classes(cls, 'add')

        @strawberry.mutation(permission_classes=permission_classes)
        def create_mutation(info, root, data: cls.create_input_type) -> cls.output_type:
            instance = cls(info, root)
            return instance.create(utils.get_data(cls.model, data))
        return create_mutation

    @classmethod
    def update_mutation(cls):
        permission_classes = get_permission_classes(cls, 'change')

        @strawberry.mutation(permission_classes=permission_classes)
        def update_mutation(info, root, data: cls.update_input_type,
                filters: Optional[List[str]] = None) -> List[cls.output_type]:
            instance = cls(info, root)
            return instance.update(utils.get_data(cls.model, data), filters=filters)

        return update_mutation

    @classmethod
    def delete_mutation(cls):
        permission_classes = get_permission_classes(cls, 'delete')

        @strawberry.mutation(permission_classes=permission_classes)
        def delete_mutation(info, root,
                filters: Optional[List[str]] = None) -> List[cls.output_type]:
            instance = cls(info, root)
            return instance.delete(filters=filters)

        return delete_mutation

    @classmethod
    def mutations(cls):
        return cls.create_mutation(), cls.update_mutation(), cls.delete_mutation()


class ModelQueryMixin:
    @classmethod
    def query(cls):
        object_name = utils.camel_to_snake(cls.model._meta.object_name)
        class Query: pass
        setattr(Query, f'{object_name}', cls.get_field())
        setattr(Query, f'{object_name}s', cls.list_field())
        return strawberry.type(Query)

    @classmethod
    def mutation(cls):
        object_name = utils.camel_to_snake(cls.model._meta.object_name)
        class Mutation: pass
        setattr(Mutation, f'create_{object_name}', cls.create_mutation())
        setattr(Mutation, f'update_{object_name}s', cls.update_mutation())
        setattr(Mutation, f'delete_{object_name}s', cls.delete_mutation())
        return strawberry.type(Mutation)


class ModelTypeBase(type):
    def __new__(cls, name, bases, attrs, **kwargs):
        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
        if hasattr(new_cls, 'model'):
            new_cls.output_type = generate_model_type(new_cls)
            new_cls.create_input_type = generate_model_type(new_cls, is_input=True)
            new_cls.update_input_type = generate_model_type(new_cls, is_input=True, is_update=True)
        return new_cls


class ModelResolver(
        ModelResolverMixin,
        ModelFieldMixin,
        ModelMutationMixin,
        ModelQueryMixin,
        metaclass=ModelTypeBase):
    pass
