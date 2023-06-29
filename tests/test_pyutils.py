from strawberry_django.utils.pyutils import (
    dicttree_insersection_differs,
    dicttree_merge,
)


def test_dicctree_merge():
    assert dicttree_merge(
        {
            "foo": 1,
            "bar": 2,
            "baz": 7,
            "sub1": {
                "a": "asub1",
                "b": "bsub1",
                "c": "csub1",
            },
            "sub2": {
                "a": "asub2",
                "b": "bsub2",
                "c": "csub2",
            },
        },
        {
            "bar": 3,
            "bin": 4,
            "sub1": {
                "a": "force_asub1",
                "d": "force_dsub1",
            },
            "sub3": {
                "a": "asub3",
                "b": "bsub3",
                "c": "csub3",
            },
        },
    ) == {
        "foo": 1,
        "bar": 3,
        "baz": 7,
        "bin": 4,
        "sub1": {
            "a": "force_asub1",
            "b": "bsub1",
            "c": "csub1",
            "d": "force_dsub1",
        },
        "sub2": {
            "a": "asub2",
            "b": "bsub2",
            "c": "csub2",
        },
        "sub3": {
            "a": "asub3",
            "b": "bsub3",
            "c": "csub3",
        },
    }


def test_dicctree_intersection_differs():
    assert not dicttree_insersection_differs({"a": 1}, {"b": 1})
    assert not dicttree_insersection_differs({"a": 1}, {"b": 2})
    assert not dicttree_insersection_differs({"a": 1}, {"a": 1})
    assert not dicttree_insersection_differs({"a": 1}, {"a": 1, "b": 1})
    assert not dicttree_insersection_differs(
        {"a": 1, "c": {"foobar": 3}},
        {"a": 1, "b": 1},
    )
    assert not dicttree_insersection_differs(
        {"a": 1, "c": {"foobar": 1}},
        {"a": 1, "b": 1, "c": {"yyy": "abc"}},
    )
    assert not dicttree_insersection_differs(
        {"a": 1, "c": {"foobar": 1}},
        {"a": 1, "b": 1, "c": {"foobar": 1}},
    )

    assert dicttree_insersection_differs({"a": 1}, {"a": 2})
    assert dicttree_insersection_differs({"a": 1}, {"a": 2, "b": 1})
    assert dicttree_insersection_differs(
        {"a": 1, "c": {"foobar": 1}},
        {"a": 2, "c": {"foobar": 1}},
    )
    assert dicttree_insersection_differs(
        {"a": 1, "c": {"foobar": 1}},
        {"a": 1, "c": {"foobar": 2}},
    )
