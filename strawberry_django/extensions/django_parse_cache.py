from strawberry.schema.execute import parse_document

from .django_cache_base import DjangoCacheBase


class DjangoParseCache(DjangoCacheBase):
    def on_parsing_start(self) -> None:
        execution_context = self.execution_context

        execution_context.graphql_document = self.execute_cached(
            parse_document,
            execution_context.query,
        )
