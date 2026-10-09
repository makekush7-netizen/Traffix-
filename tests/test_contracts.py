"""Sanity test: schemas and examples are valid JSON and example messages parse."""
import json, pathlib
import copy
import pytest
from jsonschema import ValidationError
from jsonschema import Draft202012Validator

C = pathlib.Path(__file__).resolve().parent.parent / "contracts"

def load(name):
    return json.loads((C / name).read_text(encoding="utf-8"))

def test_schemas_are_valid():
    for name in ["contracts.schema.json", "scenario.schema.json"]:
        Draft202012Validator.check_schema(load(name))

def test_examples_load():
    validator = Draft202012Validator(load("contracts.schema.json"))
    for message in load("messages.example.json"):
        validator.validate(message)
    Draft202012Validator(load("scenario.schema.json")).validate(load("rain-demo.example.json"))

@pytest.mark.parametrize('change', ['negative_speed', 'extra_field', 'invalid_choice'])
def test_contract_rejections(change):
    examples = load('messages.example.json')
    message = copy.deepcopy(examples[2] if change == 'invalid_choice' else examples[0])
    if change == 'negative_speed': message['payload']['pose']['speed_mps'] = -1
    if change == 'extra_field': message['payload']['unexpected'] = True
    if change == 'invalid_choice': message['payload']['choice'] = 'auto_accept'
    with pytest.raises(ValidationError):
        Draft202012Validator(load('contracts.schema.json')).validate(message)
