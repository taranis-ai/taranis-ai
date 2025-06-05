from frontend.utils.form_data_parser import parse_formdata
from werkzeug.datastructures import ImmutableMultiDict


def test_parse_formdata():
    formdata = ImmutableMultiDict(
        [
            ("name", "John"),
            ("age", "30"),
            ("address[city]", "New York"),
            ("address[state]", "NY"),
        ]
    )
    expected = {"name": "John", "age": "30", "address": {"city": "New York", "state": "NY"}}
    assert parse_formdata(formdata) == expected


def test_parse_formdata_with_list():
    formdata = ImmutableMultiDict(
        [
            ("items[]", "item1"),
            ("items[]", "item2"),
            ("details[0][key]", "value1"),
            ("details[0][value]", "value2"),
            ("details[1][key]", "value3"),
            ("details[1][value]", "value4"),
        ]
    )
    expected = {
        "items": ["item1", "item2"],
        "details": {
            "0": {"key": "value1", "value": "value2"},
            "1": {"key": "value3", "value": "value4"},
        },
    }
    assert parse_formdata(formdata) == expected


def test_parse_formdata_empty():
    formdata = ImmutableMultiDict([])
    expected = {}
    assert parse_formdata(formdata) == expected


def test_parse_formdata_no_nested():
    formdata = ImmutableMultiDict([("key1", "value1"), ("key2", "value2")])
    expected = {"key1": "value1", "key2": "value2"}
    assert parse_formdata(formdata) == expected


def test_parse_formdata_with_empty_values():
    formdata = ImmutableMultiDict([("name", ""), ("age", "30"), ("address[city]", "")])
    expected = {"name": "", "age": "30", "address": {"city": ""}}
    assert parse_formdata(formdata) == expected


def test_parse_formdata_with_list_of_dicts():
    formdata = ImmutableMultiDict(
        [
            ("title", "XXX"),
            ("description", "XXX"),
            ("attribute_groups[][index]", "0"),
            ("attribute_groups[][title]", "XXX"),
            ("attribute_groups[][description]", "uiae"),
        ]
    )
    expected = {
        "title": "XXX",
        "description": "XXX",
        "attribute_groups": [
            {"index": "0", "title": "XXX", "description": "uiae"},
        ],
    }
    assert parse_formdata(formdata) == expected
