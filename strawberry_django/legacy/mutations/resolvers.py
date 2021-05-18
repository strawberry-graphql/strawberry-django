from typing import List, Optional
import strawberry
from .. import fields, hooks, utils
from ..type import generate_partial_input
from ..queries.arguments import resolve_type_args
from ...resolvers import django_resolver

def create(*args, types=None, pre_save=None, post_save=None):
    model, output_type, input_type = resolve_type_args(args, types=types, is_input=True, single=True)
    @hooks.add(pre_save=pre_save, post_save=post_save)
    @strawberry.mutation
    @django_resolver
    def mutation(info, data: input_type) -> output_type:
        instance_data = utils.get_input_data(model, data)
        instance = model(**instance_data)
        def caller(hook):
            hook(info, instance)
        mutation._call_hooks('pre_save', caller)
        instance.save()
        update_m2m_fields(model, [instance], data)
        mutation._call_hooks('post_save', caller)
        return instance
    return mutation

def create_batch(*args, types=None, pre_save=None, post_save=None):
    model, output_type, input_type = resolve_type_args(args, types=types, is_input=True, single=True)
    @hooks.add(pre_save=pre_save, post_save=post_save)
    @strawberry.mutation
    @django_resolver
    def mutation(data: List[input_type]) -> List[output_type]:
        instances = []
        for d in data:
            instance_data = utils.get_input_data(model, d)
            instance = model(**instance_data)
            def caller(hook):
                hook(info=info, instance=instance)
            mutation._call_hooks('pre_save', caller)
            instance.save()
            update_m2m_fields(model, [instance], data)
            mutation._call_hooks('post_save', caller)
            instances.append(instance)
        return instances
    return mutation

def update(*args, types=None):
    model, output_type, input_type = resolve_type_args(args, types=types, is_input=True, single=True)
    update_type = generate_partial_input(model, input_type)
    @strawberry.mutation
    @django_resolver
    def mutation(data: update_type, filters: Optional[List[str]] = []) -> List[output_type]:
        qs = model.objects.all()
        if filters:
            filter, exclude = utils.process_filters(filters)
            qs = qs.filter(**filter).exclude(**exclude)
        update_data = utils.get_input_data(model, data)
        qs.update(**update_data)
        update_m2m_fields(model, qs, data)
        return qs.all()
    return mutation

def delete(*args, types=None):
    model, output_type, input_type = resolve_type_args(args, types=types, is_input=True, single=True)
    @strawberry.mutation
    @django_resolver
    def mutation(filters: Optional[List[str]] = []) -> List[strawberry.ID]:
        qs = model.objects.all()
        if filters:
            filter, exclude = utils.process_filters(filters)
            qs = qs.filter(**filter).exclude(**exclude)
        ids = list(qs.values_list('id', flat=True))
        qs.delete()
        return ids
    return mutation


#internal helpers

def update_m2m_fields(model, objects, data):
    data = utils.get_input_data_m2m(model, data)
    if not data:
        return
    # iterate through objects and update m2m fields
    for obj in objects:
        for key, actions in data.items():
            relation_field = getattr(obj, key)
            for key, values in actions.items():
                if key == 'add':
                    relation_field.add(*values)
                elif key == 'set':
                    relation_field.set(values)
                elif key == 'remove':
                    relation_field.remove(*values)
