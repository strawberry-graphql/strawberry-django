import pytest

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),
]

def test_sync(query, user, group, tag):
    result = query('{ users { id name group { id name tags { id name } } } }')
    assert not result.errors
    assert result.data['users'] == [{
        'id': str(user.id),
        'name': 'user',
        'group': {
            'id': str(group.id),
            'name': 'group',
            'tags': [{
                'id': str(tag.id),
                'name': 'tag',
            }]
        }
    }]


async def test_async(query, user, group, tag):
    result = await query('{ users { id name group { id name tags { id name } } } }')

    assert not result.errors
    assert result.data['users'] == [{
        'id': str(user.id),
        'name': 'user',
        'group': {
            'id': str(group.id),
            'name': 'group',
            'tags': [{
                'id': str(tag.id),
                'name': 'tag',
            }]
        }
    }]


def test_filters(query, user):
    result = query('{ groups { users(filters: ["name__startswith=\'us\'", "name__contains!=\'gr\'"]) { name } } }')
    assert not result.errors
    assert result.data['groups'] == [{ 'users': [{ 'name': 'user' }] }]

    result = query('{ groups { users(filters: ["name!=\'user\'"]) { name } } }')
    assert not result.errors
    assert result.data['groups'] == [{ 'users': [] }]


def test_ordering(query, users):
    result = query('{ users(orderBy: [ "-name" ]) { name } }')
    assert not result.errors
    assert result.data['users'] == [
        { 'name': 'user3' },
        { 'name': 'user2' },
        { 'name': 'user1' },
    ]
