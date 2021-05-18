from django.db import models
from typing import List, Optional
import inspect
import strawberry
from .. import hooks, utils
from ...resolvers import django_resolver
from .arguments import resolve_type_args


def get_object_resolver(*args, types=None):
    model, object_type = resolve_type_args(args, types=types, single=True)
    @strawberry.field
    @django_resolver
    def resolver(id: strawberry.ID) -> object_type:
        obj = model.objects.get(id=id)
        return obj
    return resolver


def get_list_resolver(*args, types=None, queryset=None):
    model, object_type = resolve_type_args(args, types=types, single=True)
    @hooks.add(queryset=queryset)
    @strawberry.field
    @django_resolver
    def resolver(info, filters: Optional[List[str]] = [], order_by: Optional[List[str]] = []) -> List[object_type]:
        class context:
            qs = model.objects.all()
        if filters:
            filter, exclude = utils.process_filters(filters)
            context.qs = context.qs.filter(**filter).exclude(**exclude)
        if order_by:
            context.qs = context.qs.order_by(*order_by)
        def queryset(hook):
            context.qs = hook(info=info, qs=context.qs)
        resolver._call_hooks('queryset', queryset)
        return context.qs
    return resolver


def get_resolver(resolver=None, field_name=None, is_relation=False, is_m2m=False):
    if resolver:
        if inspect.iscoroutinefunction(resolver):
            return resolver
        return django_resolver(resolver)

    if not is_relation:
        if field_name:
            def resolver(root):
                return getattr(root, field_name)
            return resolver
        return None

    if is_m2m:
        def resolver(root, info, filters: Optional[List[str]] = [], order_by: Optional[List[str]] = []):
            return get_instance_field(root, field_name, info, filters, order_by)
        return resolver

    else:
        def resolver(root, info):
            return get_instance_field(root, field_name, info)
        return resolver

@django_resolver
def get_instance_field(instance, field_name, info=None, filters=None, order_by=None):
    attr = getattr(instance, field_name or info.field_name)
    if not isinstance(attr, (models.QuerySet, models.Manager)):
        return attr

    # m2m
    qs = attr.all()
    if filters:
        filter, exclude = utils.process_filters(filters)
        qs = qs.filter(**filter).exclude(**exclude)
    if order_by:
        qs = qs.order_by(*order_by)
    return qs

