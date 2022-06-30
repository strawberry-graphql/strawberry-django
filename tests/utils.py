import dataclasses

import strawberry

import strawberry_django


def generate_query(query=None, mutation=None):
    append_mutation = mutation and not query
    if query is None:

        @strawberry.type
        class Query:
            x: int

        query = Query
    schema = strawberry.Schema(query=query, mutation=mutation)

    def process_result(result):
        return result

    async def query_async(query, variable_values, context_value):
        result = await schema.execute(
            query, variable_values=variable_values, context_value=context_value
        )
        return process_result(result)

    def query_sync(query, variable_values=None, context_value=None):
        if append_mutation and not query.startswith("mutation"):
            query = f"mutation {query}"
        if strawberry_django.utils.is_async():
            return query_async(
                query,
                variable_values=variable_values,
                context_value=context_value,
            )
        result = schema.execute_sync(
            query, variable_values=variable_values, context_value=context_value
        )
        return process_result(result)

    return query_sync


def dataclass(model):
    def wrapper(cls):
        return dataclasses.dataclass(cls)

    return wrapper


def get_field(cls, field_name):
    matches = [
        field for field in cls._type_definition.fields if field.name == field_name
    ]
    try:
        return matches[0]
    except IndexError:
        raise ValueError(f"{cls} does cont contain a field named {field_name}")
