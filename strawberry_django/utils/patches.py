import django
from django.db import (
    DEFAULT_DB_ALIAS,
    NotSupportedError,
    connections,
)
from django.db.models import Q, Window
from django.db.models.fields import related_descriptors
from django.db.models.functions import RowNumber
from django.db.models.lookups import GreaterThan, LessThanOrEqual
from django.db.models.sql import Query
from django.db.models.sql.constants import INNER
from django.db.models.sql.where import AND


def apply_pagination_fix():
    """Apply pagination fix for Django 5.1 or older.

    This is based on the fix in this patch, which is going to be included in Django 5.2:
    https://code.djangoproject.com/ticket/35677#comment:9

    If can safely be removed when Django 5.2 is the minimum version we support
    """
    if django.VERSION >= (5, 2):
        return

    # This is a copy of the function, exactly as it exists on Django 4.2, 5.0 and 5.1
    # (there are no differences in this function between these versions)
    def _filter_prefetch_queryset(queryset, field_name, instances):
        predicate = Q(**{f"{field_name}__in": instances})
        db = queryset._db or DEFAULT_DB_ALIAS
        if queryset.query.is_sliced:
            if not connections[db].features.supports_over_clause:
                raise NotSupportedError(
                    "Prefetching from a limited queryset is only supported on backends "
                    "that support window functions."
                )
            low_mark, high_mark = queryset.query.low_mark, queryset.query.high_mark
            order_by = [
                expr for expr, _ in queryset.query.get_compiler(using=db).get_order_by()
            ]
            window = Window(RowNumber(), partition_by=field_name, order_by=order_by)
            predicate &= GreaterThan(window, low_mark)
            if high_mark is not None:
                predicate &= LessThanOrEqual(window, high_mark)
            queryset.query.clear_limits()

        # >> ORIGINAL CODE
        # return queryset.filter(predicate)  # noqa: ERA001
        # << ORIGINAL CODE
        # >> PATCHED CODE
        queryset.query.add_q(predicate, reuse_all_aliases=True)
        return queryset
        # << PATCHED CODE

    related_descriptors._filter_prefetch_queryset = _filter_prefetch_queryset  # type: ignore

    # This is a copy of the function, exactly as it exists on Django 4.2, 5.0 and 5.1
    # (there are no differences in this function between these versions)
    def add_q(self, q_object, reuse_all_aliases=False):
        existing_inner = {
            a for a in self.alias_map if self.alias_map[a].join_type == INNER
        }
        # >> ORIGINAL CODE
        # clause, _ = self._add_q(q_object, self.used_aliases)  # noqa: ERA001
        # << ORIGINAL CODE
        # >> PATCHED CODE
        if reuse_all_aliases:  # noqa: SIM108
            can_reuse = set(self.alias_map)
        else:
            can_reuse = self.used_aliases
        clause, _ = self._add_q(q_object, can_reuse)
        # << PATCHED CODE
        if clause:
            self.where.add(clause, AND)
        self.demote_joins(existing_inner)

    Query.add_q = add_q
