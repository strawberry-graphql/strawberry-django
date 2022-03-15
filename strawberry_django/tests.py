import json
from typing import Optional

from django.test import Client, TestCase


class StrawberryTestCase(TestCase):
    """
    Based on: https://www.sam.today/blog/testing-graphql-with-graphene-django/ and https://docs.graphene-python.org/projects/django/en/latest/testing/
    """

    def setUp(self):
        self._client = Client()

    def query(
        self,
        query: str,
        op_name: Optional[str] = None,
        variables: Optional[dict] = None,
    ):
        """
        Args:
            query (string)   - GraphQL query to run
            op_name (string) - If the query is a mutation or named query, you must
                               supply the op_name.  For annon queries ("{ ... }"),
                               should be None (default).
            variables (dict) - If provided, the $input variable in GraphQL will be set
                               to this value

        Returns:
            dict, response from graphql endpoint.  The response has the "data" key.
                  It will have the "error" key if any error happened.
        """
        body = {"query": query}
        if op_name:
            body["operation_name"] = op_name
        if variables:
            body["variables"] = variables

        resp = self._client.post(
            "/graphql", json.dumps(body), content_type="application/json"
        )
        jresp = json.loads(resp.content.decode())
        return jresp

    def assertResponseNoErrors(self, resp: dict, expected: dict):
        """
        Assert that the resp (as retuened from query) has the data from
        expected
        """
        self.assertNotIn("errors", resp, "Response had errors")
        self.assertEqual(resp["data"], expected, "Response has correct data")
