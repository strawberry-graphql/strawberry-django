from strawberry_django.legacy import utils

def test_basic_filters():
    filter, exclude = utils.process_filters(['id__gt=5', 'name="you"', 'name__contains!="me"'])
    assert filter == { 'id__gt': 5, 'name': 'you' }
    assert exclude == { 'name__contains': 'me' }

def test_is_in_filter():
    filter, exclude = utils.process_filters(['id__in=[1, 2, 3]', 'group__in!=["a", "b", "x y z"]'])
    assert filter == { 'id__in': [1, 2, 3] }
    assert exclude == { 'group__in': ['a', 'b', 'x y z'] }
