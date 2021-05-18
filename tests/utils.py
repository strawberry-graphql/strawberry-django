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
    async def query_async(query, variable_values):
        result = await schema.execute(query, variable_values=variable_values)
        return process_result(result)
    def query_sync(query, variable_values=None):
        if append_mutation and not query.startswith('mutation'):
            query = f'mutation {query}'
        if strawberry_django.utils.is_async():
            return query_async(query, variable_values=variable_values)
        result = schema.execute_sync(query, variable_values=variable_values)
        return process_result(result)
    return query_sync

def dataclass(model):
    def wrapper(cls):
        return dataclasses.dataclass(cls)
    return wrapper
