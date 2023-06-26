import dataclasses

import strawberry
from strawberry.utils.inspect import in_async_context


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
            query,
            variable_values=variable_values,
            context_value=context_value,
        )
        return process_result(result)

    def query_sync(query, variable_values=None, context_value=None):
        if append_mutation and not query.startswith("mutation"):
            query = f"mutation {query}"
        if in_async_context():
            return query_async(
                query,
                variable_values=variable_values,
                context_value=context_value,
            )
        result = schema.execute_sync(
            query,
            variable_values=variable_values,
            context_value=context_value,
        )
        return process_result(result)

    return query_sync


def dataclass(model):
    def wrapper(cls):
        return dataclasses.dataclass(cls)

    return wrapper


def deep_tuple_to_list(data: tuple) -> list:
    return_list = []
    for elem in data:
        if isinstance(elem, tuple):
            return_list.append(deep_tuple_to_list(elem))

        else:
            return_list.append(elem)

    return return_list
