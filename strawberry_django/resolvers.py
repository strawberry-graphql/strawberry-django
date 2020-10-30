from typing import List, Optional, cast
import strawberry
from . import utils
from .types import generate_model_type
from django.core import exceptions


class ModelResolverMixin:
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

    def get_queryset_filtered(self, filter):
        qs = self.get_queryset()
        if not filter:
            return qs
        filter, exclude = utils.split_filters(filter)
        if filter:
            qs = qs.filter(**filter)
        if exclude:
            qs = qs.exclude(**exclude)
        return qs

    def list(self, **filters):
        self.check_permissions('view')
        qs = self.get_queryset_filtered(**filters)
        return qs

    def get(self, id):
        self.check_permissions('view')
        qs = self.get_queryset()
        return qs.get(id=id)

    def create(self, data):
        self.check_permissions('add')
        model = self.get_model()
        instance = model(**data)
        instance.save()
        return instance

    def update(self, data, **filters):
        self.check_permissions('change')
        qs = self.get_queryset_filtered(**filters)
        qs.update(**data)
        return qs

    def delete(self, **filters):
        self.check_permissions('delete')
        qs = self.get_queryset_filtered(**filters)
        items = list(qs)
        qs.delete()
        return items

    def check_permissions(self, permission_codenames):
        _super = super()
        if hasattr(_super, 'check_permissions'):
            _super.check_permissions(permission_codenames)


class ModelPermissionMixin:
    def check_permissions(self, permission_codenames):
        if not self.request:
            return
        if isinstance(permission_codenames, str):
            permission_codenames = [permission_codenames]
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        perms = [f'{app_label}.{perm}_{model_name}' for perm in permission_codenames]
        if not self.request.user.has_perms(perms):
            raise exceptions.PermissionDenied('Permission denied')


class ModelFieldMixin:
    @classmethod
    def get_field(cls):
        @strawberry.field
        def get_field(info, root, id: strawberry.ID) -> cls.output_type:
            instance = cls(info, root)
            return instance.get(id)
        return get_field

    @classmethod
    def list_field(cls):
        @strawberry.field
        def list_field(info, root,
                filter: Optional[List[str]] = None) -> List[cls.output_type]:
            instance = cls(info, root)
            return instance.list(filter=filter)
        return list_field

    @classmethod
    def query_fields(cls):
        return cls.get_field(), cls.list_field()


class ModelMutationMixin:
    @classmethod
    def create_mutation(cls):
        @strawberry.mutation
        def create_mutation(info, root, data: cls.create_input_type) -> cls.output_type:
            instance = cls(info, root)
            return instance.create(utils.get_data(cls.model, data))
        return create_mutation

    @classmethod
    def update_mutation(cls):
        @strawberry.mutation
        def update_mutation(info, root, data: cls.update_input_type,
                filter: Optional[List[str]] = None) -> List[cls.output_type]:
            instance = cls(info, root)
            return instance.update(utils.get_data(cls.model, data), filter=filter)
        return update_mutation

    @classmethod
    def delete_mutation(cls):
        @strawberry.mutation
        def delete_mutation(info, root,
                filter: Optional[List[str]] = None) -> List[cls.output_type]:
            instance = cls(info, root)
            return instance.delete(filter=filter)
        return delete_mutation

    @classmethod
    def mutations(cls):
        return cls.create_mutation(), cls.update_mutation(), cls.delete_mutation()


class ModelQueryMixin:
    @classmethod
    def query(cls):
        verbose_name = cls.model._meta.verbose_name
        class Query: pass
        setattr(Query, f'{verbose_name}', cls.get_field())
        setattr(Query, f'{verbose_name}s', cls.list_field())
        return strawberry.type(Query)

    @classmethod
    def mutation(cls):
        verbose_name = cls.model._meta.verbose_name
        class Mutation: pass
        setattr(Mutation, f'create_{verbose_name}', cls.create_mutation())
        setattr(Mutation, f'update_{verbose_name}s', cls.update_mutation())
        setattr(Mutation, f'delete_{verbose_name}s', cls.delete_mutation())
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
        ModelPermissionMixin,
        ModelFieldMixin,
        ModelMutationMixin,
        ModelQueryMixin,
        metaclass=ModelTypeBase):
    pass
