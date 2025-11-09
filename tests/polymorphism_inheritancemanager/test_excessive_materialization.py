import re

import pytest
from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import CaptureQueriesContext

from .models import (
    ArtProject,
    ArtProjectNote,
    ArtProjectNoteDetails,
    Company,
    Project,
)
from .schema import schema


@pytest.mark.django_db(transaction=True)
def test_excessive_materialization_before_pagination_on_connection():
    # Seed data: N companies, each with one ArtProject -> note -> detail
    n = 5
    companies = []
    for i in range(n):
        c = Company.objects.create(name=f"C{i}")
        ap = ArtProject.objects.create(company=c, topic=f"Topic{i}", artist=f"A{i}")
        note = ArtProjectNote.objects.create(art_project=ap, title=f"N{i}")
        ArtProjectNoteDetails.objects.create(art_project_note=note, text=f"d{i}")
        companies.append(c)

    query = """query {
  companiesPaginated(pagination:{limit: 1}) {
    name
    projects {
      __typename
      ... on ArtProjectType {
        artNotes {
          details {  text } } }
    }
  }
}
    """

    # Capture all SQL issued during execution
    conn = connections[DEFAULT_DB_ALIAS]
    with CaptureQueriesContext(conn) as ctx:
        result = schema.execute_sync(query)

    assert not result.errors
    assert result.data is not None
    companies = result.data["companiesPaginated"]
    assert isinstance(companies, list)
    assert len(companies) == 1, (
        "Pagination (first: 1) should return exactly one element"
    )

    # Gather all SQL for debugging on failure
    all_sql = [q["sql"] for q in ctx]
    all_sql_joined = "\n".join(all_sql)

    # 1) Verify that the parent Connection (companies) is paginated at SQL level when first: 1 is used
    company_table = Company._meta.db_table
    companies_sql = [sql for sql in all_sql if company_table in sql]

    def _has_sql_level_pagination(sql: str) -> bool:
        # Accept common DB-specific pagination patterns
        return (
            re.search(r"\bLIMIT\s+1\b", sql, flags=re.IGNORECASE) is not None
            or "_strawberry_row_number" in sql  # window pagination
            or "ROW_NUMBER()" in sql
            or re.search(r"FETCH\s+FIRST\s+1\s+ROW", sql, flags=re.IGNORECASE)
            is not None
        )

    if companies_sql:
        assert any(_has_sql_level_pagination(s) for s in companies_sql), (
            "Parent Connection base queryset was materialized without pagination. "
            "Expected a LIMIT/ROW_NUMBER pagination on companies selection when requesting first: 1.\n\n"
            f"All SQL (captured):\n{all_sql_joined}"
        )

    # 2) Locate the SELECT against the Project table with an IN (...) on company_id
    project_table = Project._meta.db_table

    def find_projects_in_query(sql: str) -> bool:
        return project_table in sql

    projects_sql = [q["sql"] for q in ctx if find_projects_in_query(q["sql"])]

    # If a projects query exists, ensure it does NOT batch across multiple company ids.
    # It's acceptable that no projects query is executed if data was served from cache
    # after page-level postfetch populated it.
    if projects_sql:
        joined_sql = "\n".join(projects_sql)
        # Look for IN (...) over company_id
        m = re.search(
            r"company_id\s+IN\s*\(([^)]*)\)",
            joined_sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if m is not None:
            in_content = m.group(1)
            # If digits are present, ensure only one distinct id; otherwise ensure no comma
            if any(ch.isdigit() for ch in in_content):
                nums = [int(x) for x in re.findall(r"\b\d+\b", in_content)]
                assert len(set(nums)) <= 1, (
                    "Expected at most one company id in IN (...) clause for projects after pagination.\n\n"
                    f"All SQL (captured):\n{all_sql_joined}"
                )
            else:
                assert "," not in in_content, (
                    "Expected IN (...) to contain a single placeholder/value for projects after pagination.\n\n"
                    f"All SQL (captured):\n{all_sql_joined}"
                )
