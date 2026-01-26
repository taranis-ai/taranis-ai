import types
from typing import Union, get_args, get_origin

import lxml.html
from lxml.html import CheckboxValues, InputElement, MultipleSelectOptions
from pydantic import BaseModel
from pydantic.fields import FieldInfo


class FormData(dict):
    def __init__(self, form_element):
        super().__init__()
        self._frozen = False
        self.form = form_element

        for key, element in form_element.inputs.items():
            skip, value = self._get_value_from_element(element)
            if not skip:
                self[key] = value

        self._frozen = True

    def _get_value_from_element(self, element):
        if isinstance(element, InputElement) and element.attrib.get("type") == "submit":
            return True, None

        value = element.value

        if value is None:
            return False, ""
        if isinstance(value, str):
            value = value.lstrip("\n")
        elif isinstance(value, CheckboxValues):
            value = [el.value for el in value.group if el.value is not None]
        elif isinstance(value, MultipleSelectOptions):
            value = list(value)

        return False, value

    def __setitem__(self, key, value):
        if self._frozen and key not in self:
            available_keys = ", ".join(self.keys())
            raise ValueError(f"Key '{key}' is not in the dict. Available: {available_keys}")
        super().__setitem__(key, value)

    def update(self, other=None, **kwargs):
        if other:
            for key, value in other.items():
                self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def submit(self, client):
        for method in ["get", "post", "delete"]:
            url = self.form.get(f"hx-{method}")
            if url:
                break
        else:
            url = self.form.get("action")
            if not url:
                raise ValueError("Could not find an URL to send data to. Tried hx-get, hx-post, hx-delete and action.")
            method = self.form.get("method", "get").lower()

        return getattr(client, method)(url, self)

    def get_cleaned_keys(self):
        """
        Return the keys of the form data, excluding None and empty strings.
        """
        keys = set(dict(self).keys())
        keys.discard(None)
        return keys


def html_form_to_dict(html: str, index: int = 0, name: str | None = None, id: str | None = None) -> FormData:
    """
    Return data of a form in the given `html`.

    - index: Return the data of the n'th form in the html. Defaults to the first one.
    - name: Return the data of the form with the given name.
    - id: Return the data of the form with the given id.
    """
    tree = lxml.html.fromstring(html)

    for attr_name, attr_value in (("name", name), ("id", id)):
        if attr_value is not None:
            found_values = []
            for form in tree.iterfind(".//form"):
                val = form.get(attr_name)
                found_values.append(val)
                if val == attr_value:
                    return FormData(form)
            raise ValueError(f'No form with {attr_name}="{attr_value}" found. Found forms with these {attr_name}s: {found_values}')

    try:
        return FormData(tree.forms[index])
    except IndexError as e:
        raise ValueError(f"No form at index {index}. Found {len(tree.forms)} forms.") from e


def gather_fields_from_model(model: type[BaseModel]) -> tuple[set[str], set[str]]:
    """
    Given a Pydantic model class, return the set of its direct field names,
    with list‐fields rendered as 'foo[]'. Does NOT recurse further.
    """
    allowed_keys = set()
    required_keys = set()

    for name, info in model.model_fields.items():
        if name == "id":
            continue

        info: FieldInfo = info
        ann = info.annotation
        field_required = True
        if nested_origin := unwrap_annotation(ann):
            ann = nested_origin[0]
            field_required = nested_origin[1]

        key = f"{name}[]" if get_origin(ann) is list else name

        allowed_keys.add(key)
        if field_required:
            required_keys.add(key)
    return allowed_keys, required_keys


def unwrap_annotation(field_annotation: type | None) -> tuple[type, bool] | None:
    """If field_annotation is a Union or PEP604 union, return its first arg, else ann itself."""
    if field_annotation is None:
        return None
    ann: type = field_annotation
    field_required = True
    if field_annotation is Union or isinstance(field_annotation, types.UnionType):
        if args := get_args(field_annotation):
            ann = args[0]
            if None not in args:
                field_required = False

    return ann, field_required
