"""Compatibility layer for graphql-core 3.2.x and 3.3.x."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from graphql import (
    FieldNode,
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLObjectType,
    get_argument_values,
)
from graphql.version import VersionInfo, version_info

if TYPE_CHECKING:
    from graphql.type.definition import GraphQLResolveInfo

IS_GQL_33 = version_info >= VersionInfo.from_str("3.3.0a0")
IS_GQL_32 = not IS_GQL_33


def _get_variable_values(info: GraphQLResolveInfo) -> Any:
    if IS_GQL_32:
        return info.variable_values

    from graphql.execution.values import VariableValues  # type: ignore

    # Strawberry exposes the coerced variables as a dict on resolve info.
    return VariableValues(sources={}, coerced=info.variable_values)


def get_field_arguments(
    info: GraphQLResolveInfo,
    field: GraphQLField,
    node: FieldNode,
) -> dict[str, Any]:
    return get_argument_values(field, node, _get_variable_values(info))


def get_sub_field_selections(
    info: GraphQLResolveInfo,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
) -> dict[str, list[FieldNode]]:
    """Collect sub-fields, handling API differences between 3.2.x and 3.3.x."""
    if IS_GQL_32:
        return _get_selections_gql32(info, parent_type)
    return _get_selections_gql33(info, parent_type)


def _get_selections_gql32(
    info: GraphQLResolveInfo,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
) -> dict[str, list[FieldNode]]:
    from graphql.execution.collect_fields import (
        collect_sub_fields,
    )

    return collect_sub_fields(
        info.schema,
        info.fragments,
        info.variable_values,
        cast("GraphQLObjectType", parent_type),
        info.field_nodes,
    )


def _get_selections_gql33(
    info: GraphQLResolveInfo,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
) -> dict[str, list[FieldNode]]:
    from graphql.execution.collect_fields import (
        FieldDetails,  # type: ignore
        FragmentDetails,  # type: ignore
        collect_subfields,  # type: ignore
    )

    field_group: list[Any] = [
        FieldDetails(node=fn, defer_usage=None) for fn in info.field_nodes
    ]

    collected = collect_subfields(
        info.schema,
        {name: FragmentDetails(fragment) for name, fragment in info.fragments.items()},
        _get_variable_values(info),
        info.operation,
        cast("GraphQLObjectType", parent_type),
        field_group,
    )

    return {
        key: [fd.node for fd in field_details]
        for key, field_details in collected.grouped_field_set.items()
    }
