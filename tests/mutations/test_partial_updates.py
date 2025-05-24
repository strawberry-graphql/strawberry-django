"""Tests the behaviour of partial input optional fields in mutations.

This module tests Strawberry-Django's handling of partial input optional fields in
mutations, specifically when their values are omitted or explicitly set to `null`, for
different variations of model fields:

* Required fields
* Optional and nullable fields
* Optional and non-nullable fields
* Required foreign key fields
* Optional foreign key fields
* Many-to-many fields

These tests stem from the fact that the GraphQL type-system doesn't distinguish between
optional and nullable. That is, type `T!` is both required and non-nullable (i.e., must
be supplied and cannot be `null`), but type `T` is both optional and nullable (i.e., can
be omitted and can be `null`).
"""

import pytest
import strawberry
from django.test import override_settings
from strawberry.relay import to_base64

import strawberry_django
from strawberry_django.settings import strawberry_django_settings
from tests.projects.faker import (
    IssueFactory,
    MilestoneFactory,
    ProjectFactory,
    TagFactory,
)
from tests.projects.models import Issue, Milestone, Project, Tag
from tests.utils import generate_query


@pytest.fixture
def mutation(db):
    @strawberry_django.type(Issue)
    class IssueType:
        id: strawberry.auto
        name: strawberry.auto
        kind: strawberry.auto
        priority: strawberry.auto
        milestone: strawberry.auto
        tags: strawberry.auto

    @strawberry_django.partial(Issue)
    class IssueInputPartial:
        id: strawberry.auto
        name: strawberry.auto
        kind: strawberry.auto
        priority: strawberry.auto
        milestone: strawberry.auto
        tags: strawberry.auto

    @strawberry_django.type(Milestone)
    class MilestoneType:
        id: strawberry.auto
        project: strawberry.auto

    @strawberry_django.partial(Milestone)
    class MilestoneInputPartial:
        id: strawberry.auto
        project: strawberry.auto

    @strawberry_django.type(Project)
    class ProjectType:
        id: strawberry.auto

    @strawberry_django.type(Tag)
    class TagType:
        id: strawberry.auto

    @strawberry.type
    class Query:
        issue: IssueType
        milestone: MilestoneType
        project: ProjectType
        tag: TagType

    @strawberry.type
    class Mutation:
        update_issue: IssueType = strawberry_django.mutations.update(
            IssueInputPartial,
            handle_django_errors=True,
        )
        update_milestone: MilestoneType = strawberry_django.mutations.update(
            MilestoneInputPartial,
            handle_django_errors=True,
        )

    return generate_query(query=Query, mutation=Mutation)


def test_field_required(mutation):
    """Tests behaviour for a required model field."""
    query = """mutation UpdateIssueName($id: ID!, $name: String) {
      updateIssue(data: { id: $id, name: $name }) {
        ...on IssueType {
          name
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    issue_name = "Original name"
    issue = IssueFactory.create(name=issue_name)

    # Update the issue, omitting the `name` field
    # We expect the mutation to succeed and the name to remain unchanged
    result = mutation(query, {"id": issue.pk})
    assert result.errors is None
    assert result.data == {"updateIssue": {"name": issue_name}}
    issue.refresh_from_db()
    assert issue.name == issue_name

    # Update the issue, explicitly providing `null` for the `name` field
    # We expect the mutation to fail and the name to remain unchanged
    # Note that this failure occurs at the model level, not the GraphQL level
    result = mutation(query, {"id": issue.pk, "name": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {
            "messages": [
                {
                    "kind": "VALIDATION",
                    "code": "null",
                    "message": "This field cannot be null.",
                    "field": "name",
                }
            ]
        }
    }
    issue.refresh_from_db()
    assert issue.name == issue_name


def test_field_optional_and_non_nullable(mutation):
    """Tests behaviour for an optional & non-nullable model field."""
    query = """mutation UpdateIssuePriority($id: ID!, $priority: Int) {
      updateIssue(data: { id: $id, priority: $priority }) {
        ...on IssueType {
          priority
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    issue_priority = 42
    issue = IssueFactory.create(priority=issue_priority)

    # Update the issue, omitting the `priority` field
    # We expect the mutation to succeed and the priority to remain unchanged
    result = mutation(query, {"id": issue.pk})
    assert result.errors is None
    assert result.data == {"updateIssue": {"priority": issue_priority}}
    issue.refresh_from_db()
    assert issue.priority == issue_priority

    # Update the issue, explicitly providing `null` for the `priority` field
    # We expect the mutation to fail and the priority to remain unchanged
    # Note that this failure occurs at the model level, not the GraphQL level
    result = mutation(query, {"id": issue.pk, "priority": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {
            "messages": [
                {
                    "kind": "VALIDATION",
                    "code": "null",
                    "message": "This field cannot be null.",
                    "field": "priority",
                }
            ]
        }
    }
    issue.refresh_from_db()
    assert issue.priority == issue_priority


def test_field_optional_and_nullable(mutation):
    """Tests behaviour for an optional & nullable model field."""
    query = """mutation UpdateIssueKind($id: ID!, $kind: String) {
      updateIssue(data: { id: $id, kind: $kind }) {
        ...on IssueType {
          kind
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    issue_kind = Issue.Kind.FEATURE.value
    issue = IssueFactory.create(kind=issue_kind)

    # Update the issue, omitting the `kind` field
    # We expect the mutation to succeed and the kind to remain unchanged
    result = mutation(query, {"id": issue.pk})
    assert result.errors is None
    assert result.data == {"updateIssue": {"kind": issue_kind}}
    issue.refresh_from_db()
    assert issue.kind == issue_kind

    # Update the issue, explicitly providing `null` for the `kind` field
    # We expect the mutation to succeed and the kind to be set to `None`
    result = mutation(query, {"id": issue.pk, "kind": None})
    assert result.errors is None
    assert result.data == {"updateIssue": {"kind": None}}
    issue.refresh_from_db()
    assert issue.kind is None


def test_foreign_key_required(mutation):
    """Tests behaviour for a required foreign key field."""
    query = """mutation UpdateMilestoneProject($id: ID!, $project: OneToManyInput) {
      updateMilestone(data: { id: $id, project: $project }) {
        ...on MilestoneType {
          project { pk }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create a milestone
    project = ProjectFactory.create()
    milestone = MilestoneFactory.create(project=project)

    # Update the milestone, omitting the `project` field
    # We expect the mutation to succeed and the project to remain unchanged
    result = mutation(query, {"id": milestone.pk})
    assert result.errors is None
    assert result.data == {"updateMilestone": {"project": {"pk": str(project.pk)}}}
    milestone.refresh_from_db()
    assert milestone.project == project

    # Update the milestone, explicitly providing `null` for the `project` field
    # We expect the mutation to fail and the project to remain unchanged
    # Note that this failure occurs at the model level, not the GraphQL level
    result = mutation(query, {"id": milestone.pk, "project": None})
    assert result.errors is None
    assert result.data == {
        "updateMilestone": {
            "messages": [
                {
                    "kind": "VALIDATION",
                    "code": "null",
                    "message": "This field cannot be null.",
                    "field": "project",
                }
            ]
        }
    }
    milestone.refresh_from_db()
    assert milestone.project == project


def test_foreign_key_optional(mutation):
    """Tests behaviour for an optional foreign key field."""
    query = """mutation UpdateIssueMilestone($id: ID!, $milestone: OneToManyInput) {
      updateIssue(data: { id: $id, milestone: $milestone }) {
        ...on IssueType {
          milestone { pk }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    milestone = MilestoneFactory.create()
    issue = IssueFactory.create(milestone=milestone)

    # Update the issue, omitting the `milestone` field
    # We expect the mutation to succeed and the milestone to remain unchanged
    result = mutation(query, {"id": issue.pk})
    assert result.errors is None
    assert result.data == {"updateIssue": {"milestone": {"pk": str(milestone.pk)}}}
    issue.refresh_from_db()
    assert issue.milestone == milestone

    # Update the issue, explicitly providing `null` for the `milestone` field
    # We expect the mutation to succeed and the milestone to be set to `None`
    result = mutation(query, {"id": issue.pk, "milestone": None})
    assert result.errors is None
    assert result.data == {"updateIssue": {"milestone": None}}
    issue.refresh_from_db()
    assert issue.milestone is None


def test_many_to_many(mutation):
    """Tests behaviour for a many to many field."""
    query = """mutation UpdateIssueTags($id: ID!, $tags: ManyToManyInput) {
      updateIssue(data: { id: $id, tags: $tags }) {
        ...on IssueType {
          tags { pk }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    tags = TagFactory.create_batch(3)
    issue = IssueFactory.create()
    issue.tags.set(tags)

    # Update the issue, omitting the `tags` field
    # We expect the mutation to succeed and the tags to remain unchanged
    result = mutation(query, {"id": issue.pk})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"pk": str(tag.pk)} for tag in tags]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing `null` for the `tags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = mutation(query, {"id": issue.pk, "tags": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"pk": str(tag.pk)} for tag in tags]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags


def test_many_to_many_set(mutation):
    """Tests behaviour for `set` on a many to many field."""
    query = """mutation SetIssueTags($id: ID!, $setTags: [ID!]) {
      updateIssue(data: { id: $id, tags: { set: $setTags } }) {
        ...on IssueType {
          tags { pk }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    tags = TagFactory.create_batch(3)
    issue = IssueFactory.create()
    issue.tags.set(tags)

    # Update the issue, omitting the `setTags` field
    # We expect the mutation to succeed and the tags to remain unchanged
    result = mutation(query, {"id": issue.pk})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"pk": str(tag.pk)} for tag in tags]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing `null` for the `setTags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = mutation(query, {"id": issue.pk, "setTags": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"pk": str(tag.pk)} for tag in tags]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing an empty list for the `setTags` field
    # We expect the mutation to succeed, and the tags to be cleared
    result = mutation(query, {"id": issue.pk, "setTags": []})
    assert result.errors is None
    assert result.data == {"updateIssue": {"tags": []}}
    issue.refresh_from_db()
    assert list(issue.tags.all()) == []


def test_many_to_many_add(mutation):
    """Tests behaviour for `add` on a many to many field."""
    query = """mutation AddIssueTags($id: ID!, $addTags: [ID!]) {
      updateIssue(data: { id: $id, tags: { add: $addTags } }) {
        ...on IssueType {
          tags { pk }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    tags = TagFactory.create_batch(3)
    issue = IssueFactory.create()
    issue.tags.set(tags)

    # Update the issue, omitting the `addTags` field
    # We expect the mutation to succeed and the tags to remain unchanged
    result = mutation(query, {"id": issue.pk})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"pk": str(tag.pk)} for tag in tags]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing `null` for the `addTags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = mutation(query, {"id": issue.pk, "addTags": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"pk": str(tag.pk)} for tag in tags]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing an empty list for the `addTags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = mutation(query, {"id": issue.pk, "addTags": []})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"pk": str(tag.pk)} for tag in tags]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags


def test_many_to_many_remove(mutation):
    """Tests behaviour for `remove` on a many to many field."""
    query = """mutation RemoveIssueTags($id: ID!, $removeTags: [ID!]) {
      updateIssue(data: { id: $id, tags: { remove: $removeTags } }) {
        ...on IssueType {
          tags { pk }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    tags = TagFactory.create_batch(3)
    issue = IssueFactory.create()
    issue.tags.set(tags)

    # Update the issue, omitting the `removeTags` field
    # We expect the mutation to succeed and the tags to remain unchanged
    result = mutation(query, {"id": issue.pk})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"pk": str(tag.pk)} for tag in tags]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing `null` for the `removeTags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = mutation(query, {"id": issue.pk, "removeTags": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"pk": str(tag.pk)} for tag in tags]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing an empty list for the `removeTags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = mutation(query, {"id": issue.pk, "removeTags": []})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"pk": str(tag.pk)} for tag in tags]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags


@pytest.fixture
@override_settings(
    STRAWBERRY_DJANGO={
        **strawberry_django_settings(),
        "MAP_AUTO_ID_AS_GLOBAL_ID": True,
    },
)
def relay_mutation(db):
    @strawberry_django.type(Issue)
    class IssueType(strawberry.relay.Node):
        name: strawberry.auto
        kind: strawberry.auto
        priority: strawberry.auto
        milestone: strawberry.auto
        tags: strawberry.auto

    @strawberry_django.partial(Issue)
    class IssueInputPartial(strawberry_django.NodeInput):
        name: strawberry.auto
        kind: strawberry.auto
        priority: strawberry.auto
        milestone: strawberry.auto
        tags: strawberry.auto

    @strawberry_django.type(Milestone)
    class MilestoneType(strawberry.relay.Node):
        project: strawberry.auto

    @strawberry_django.partial(Milestone)
    class MilestoneInputPartial(strawberry_django.NodeInput):
        project: strawberry.auto

    @strawberry_django.type(Project)
    class ProjectType(strawberry.relay.Node):
        pass

    @strawberry_django.type(Tag)
    class TagType(strawberry.relay.Node):
        pass

    @strawberry.type
    class Query:
        issue: IssueType
        milestone: MilestoneType
        project: ProjectType
        tag: TagType

    @strawberry.type
    class Mutation:
        update_issue: IssueType = strawberry_django.mutations.update(
            IssueInputPartial,
            handle_django_errors=True,
        )
        update_milestone: MilestoneType = strawberry_django.mutations.update(
            MilestoneInputPartial,
            handle_django_errors=True,
        )

    return generate_query(query=Query, mutation=Mutation)


def test_relay_field_required(relay_mutation):
    """Tests Relay behaviour for a required model field."""
    query = """mutation UpdateIssueName($id: ID!, $name: String) {
      updateIssue(data: { id: $id, name: $name }) {
        ...on IssueType {
          name
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    issue_name = "Original name"
    issue = IssueFactory.create(name=issue_name)
    issue_id = to_base64("IssueType", issue.pk)

    # Update the issue, omitting the `name` field
    # We expect the mutation to succeed and the name to remain unchanged
    result = relay_mutation(query, {"id": issue_id})
    assert result.errors is None
    assert result.data == {"updateIssue": {"name": issue_name}}
    issue.refresh_from_db()
    assert issue.name == issue_name

    # Update the issue, explicitly providing `null` for the `name` field
    # We expect the mutation to fail and the name to remain unchanged
    # Note that this failure occurs at the model level, not the GraphQL level
    result = relay_mutation(query, {"id": issue_id, "name": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {
            "messages": [
                {
                    "kind": "VALIDATION",
                    "code": "null",
                    "message": "This field cannot be null.",
                    "field": "name",
                }
            ]
        }
    }
    issue.refresh_from_db()
    assert issue.name == issue_name


def test_relay_field_optional_and_non_nullable(relay_mutation):
    """Tests Relay behaviour for an optional & non-nullable model field."""
    query = """mutation UpdateIssuePriority($id: ID!, $priority: Int) {
      updateIssue(data: { id: $id, priority: $priority }) {
        ...on IssueType {
          priority
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    issue_priority = 42
    issue = IssueFactory.create(priority=issue_priority)
    issue_id = to_base64("IssueType", issue.pk)

    # Update the issue, omitting the `priority` field
    # We expect the mutation to succeed and the priority to remain unchanged
    result = relay_mutation(query, {"id": issue_id})
    assert result.errors is None
    assert result.data == {"updateIssue": {"priority": issue_priority}}
    issue.refresh_from_db()
    assert issue.priority == issue_priority

    # Update the issue, explicitly providing `null` for the `priority` field
    # We expect the mutation to fail and the priority to remain unchanged
    # Note that this failure occurs at the model level, not the GraphQL level
    result = relay_mutation(query, {"id": issue_id, "priority": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {
            "messages": [
                {
                    "kind": "VALIDATION",
                    "code": "null",
                    "message": "This field cannot be null.",
                    "field": "priority",
                }
            ]
        }
    }
    issue.refresh_from_db()
    assert issue.priority == issue_priority


def test_relay_field_optional_and_nullable(relay_mutation):
    """Tests Relay behaviour for an optional & nullable model field."""
    query = """mutation UpdateIssueKind($id: ID!, $kind: String) {
      updateIssue(data: { id: $id, kind: $kind }) {
        ...on IssueType {
          kind
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    issue_kind = Issue.Kind.FEATURE.value
    issue = IssueFactory.create(kind=issue_kind)
    issue_id = to_base64("IssueType", issue.pk)

    # Update the issue, omitting the `kind` field
    # We expect the mutation to succeed and the kind to remain unchanged
    result = relay_mutation(query, {"id": issue_id})
    assert result.errors is None
    assert result.data == {"updateIssue": {"kind": issue_kind}}
    issue.refresh_from_db()
    assert issue.kind == issue_kind

    # Update the issue, explicitly providing `null` for the `kind` field
    # We expect the mutation to succeed and the kind to be set to `None`
    result = relay_mutation(query, {"id": issue_id, "kind": None})
    assert result.errors is None
    assert result.data == {"updateIssue": {"kind": None}}
    issue.refresh_from_db()
    assert issue.kind is None


def test_relay_foreign_key_required(relay_mutation):
    """Tests Relay behaviour for a required foreign key field."""
    query = """mutation UpdateMilestoneProject($id: ID!, $project: NodeInput) {
      updateMilestone(data: { id: $id, project: $project }) {
        ...on MilestoneType {
          project { id }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create a milestone
    project = ProjectFactory.create()
    project_id = to_base64("ProjectType", project.pk)
    milestone = MilestoneFactory.create(project=project)
    milestone_id = to_base64("MilestoneType", milestone.pk)

    # Update the milestone, omitting the `project` field
    # We expect the mutation to succeed and the project to remain unchanged
    result = relay_mutation(query, {"id": milestone_id})
    assert result.errors is None
    assert result.data == {"updateMilestone": {"project": {"id": project_id}}}
    milestone.refresh_from_db()
    assert milestone.project == project

    # Update the milestone, explicitly providing `null` for the `project` field
    # We expect the mutation to fail and the project to remain unchanged
    # Note that this failure occurs at the model level, not the GraphQL level
    result = relay_mutation(query, {"id": milestone_id, "project": None})
    assert result.errors is None
    assert result.data == {
        "updateMilestone": {
            "messages": [
                {
                    "kind": "VALIDATION",
                    "code": "null",
                    "message": "This field cannot be null.",
                    "field": "project",
                }
            ]
        }
    }
    milestone.refresh_from_db()
    assert milestone.project == project


def test_relay_foreign_key_optional(relay_mutation):
    """Tests Relay behaviour for an optional foreign key field."""
    query = """mutation UpdateIssueMilestone($id: ID!, $milestone: NodeInput) {
      updateIssue(data: { id: $id, milestone: $milestone }) {
        ...on IssueType {
          milestone { id }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    milestone = MilestoneFactory.create()
    milestone_id = to_base64("MilestoneType", milestone.pk)
    issue = IssueFactory.create(milestone=milestone)
    issue_id = to_base64("IssueType", issue.pk)

    # Update the issue, omitting the `milestone` field
    # We expect the mutation to succeed and the milestone to remain unchanged
    result = relay_mutation(query, {"id": issue_id})
    assert result.errors is None
    assert result.data == {"updateIssue": {"milestone": {"id": milestone_id}}}
    issue.refresh_from_db()
    assert issue.milestone == milestone

    # Update the issue, explicitly providing `null` for the `milestone` field
    # We expect the mutation to succeed and the milestone to be set to `None`
    result = relay_mutation(query, {"id": issue_id, "milestone": None})
    assert result.errors is None
    assert result.data == {"updateIssue": {"milestone": None}}
    issue.refresh_from_db()
    assert issue.milestone is None


def test_relay_many_to_many(relay_mutation):
    """Tests Relay behaviour for a many to many field."""
    query = """mutation UpdateIssueTags($id: ID!, $tags: NodeInputListInput) {
      updateIssue(data: { id: $id, tags: $tags }) {
        ...on IssueType {
          tags { id }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    tags = TagFactory.create_batch(3)
    tag_ids = [to_base64("TagType", tag.pk) for tag in tags]
    issue = IssueFactory.create()
    issue.tags.set(tags)
    issue_id = to_base64("IssueType", issue.pk)

    # Update the issue, omitting the `tags` field
    # We expect the mutation to succeed and the tags to remain unchanged
    result = relay_mutation(query, {"id": issue_id})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"id": tag_id} for tag_id in tag_ids]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing `null` for the `tags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = relay_mutation(query, {"id": issue_id, "tags": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"id": tag_id} for tag_id in tag_ids]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags


def test_relay_many_to_many_set(relay_mutation):
    """Tests Relay behaviour for `set` on a many to many field."""
    query = """mutation SetIssueTags($id: ID!, $setTags: [NodeInput!]) {
      updateIssue(data: { id: $id, tags: { set: $setTags } }) {
        ...on IssueType {
          tags { id }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    tags = TagFactory.create_batch(3)
    tag_ids = [to_base64("TagType", tag.pk) for tag in tags]
    issue = IssueFactory.create()
    issue.tags.set(tags)
    issue_id = to_base64("IssueType", issue.pk)

    # Update the issue, omitting the `setTags` field
    # We expect the mutation to succeed and the tags to remain unchanged
    result = relay_mutation(query, {"id": issue_id})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"id": tag_id} for tag_id in tag_ids]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing `null` for the `setTags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = relay_mutation(query, {"id": issue_id, "setTags": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"id": tag_id} for tag_id in tag_ids]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing an empty list for the `setTags` field
    # We expect the mutation to succeed, and the tags to be cleared
    result = relay_mutation(query, {"id": issue_id, "setTags": []})
    assert result.errors is None
    assert result.data == {"updateIssue": {"tags": []}}
    issue.refresh_from_db()
    assert list(issue.tags.all()) == []


def test_relay_many_to_many_add(relay_mutation):
    """Tests Relay behaviour for `add` on a many to many field."""
    query = """mutation AddIssueTags($id: ID!, $addTags: [NodeInput!]) {
      updateIssue(data: { id: $id, tags: { add: $addTags } }) {
        ...on IssueType {
          tags { id }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    tags = TagFactory.create_batch(3)
    tag_ids = [to_base64("TagType", tag.pk) for tag in tags]
    issue = IssueFactory.create()
    issue.tags.set(tags)
    issue_id = to_base64("IssueType", issue.pk)

    # Update the issue, omitting the `addTags` field
    # We expect the mutation to succeed and the tags to remain unchanged
    result = relay_mutation(query, {"id": issue_id})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"id": tag_id} for tag_id in tag_ids]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing `null` for the `addTags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = relay_mutation(query, {"id": issue_id, "addTags": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"id": tag_id} for tag_id in tag_ids]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing an empty list for the `addTags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = relay_mutation(query, {"id": issue_id, "addTags": []})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"id": tag_id} for tag_id in tag_ids]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags


def test_relay_many_to_many_remove(relay_mutation):
    """Tests Relay behaviour for `remove` on a many to many field."""
    query = """mutation RemoveIssueTags($id: ID!, $removeTags: [NodeInput!]) {
      updateIssue(data: { id: $id, tags: { remove: $removeTags } }) {
        ...on IssueType {
          tags { id }
        }
        ... on OperationInfo {
          messages {
            kind
            code
            message
            field
          }
        }
      }
    }
    """

    # Create an issue
    tags = TagFactory.create_batch(3)
    tag_ids = [to_base64("TagType", tag.pk) for tag in tags]
    issue = IssueFactory.create()
    issue.tags.set(tags)
    issue_id = to_base64("IssueType", issue.pk)

    # Update the issue, omitting the `removeTags` field
    # We expect the mutation to succeed and the tags to remain unchanged
    result = relay_mutation(query, {"id": issue_id})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"id": tag_id} for tag_id in tag_ids]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing `null` for the `removeTags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = relay_mutation(query, {"id": issue_id, "removeTags": None})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"id": tag_id} for tag_id in tag_ids]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags

    # Update the issue, explicitly providing an empty list for the `removeTags` field
    # We expect the mutation to succeed, but the tags to remain unchanged
    result = relay_mutation(query, {"id": issue_id, "removeTags": []})
    assert result.errors is None
    assert result.data == {
        "updateIssue": {"tags": [{"id": tag_id} for tag_id in tag_ids]}
    }
    issue.refresh_from_db()
    assert list(issue.tags.all()) == tags
