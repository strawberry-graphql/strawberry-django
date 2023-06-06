def test_query(query, user, group, tag):
    result = query("{ users { id name group { id name tags { id name } } } }")
    assert not result.errors
    assert result.data["users"] == [
        {
            "id": str(user.id),
            "name": "user",
            "group": {
                "id": str(group.id),
                "name": "group",
                "tags": [
                    {
                        "id": str(tag.id),
                        "name": "tag",
                    },
                ],
            },
        },
    ]
