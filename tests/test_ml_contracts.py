import json
from pathlib import Path
from jsonschema import Draft202012Validator
from ml.integration import TrafficIntelligence


def test_original_contract_examples_and_ml_payloads_validate():
    root=Path(__file__).resolve().parents[1]/'contracts'
    schema=json.loads((root/'contracts.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    validator=Draft202012Validator(schema)
    for message in json.loads((root/'messages.example.json').read_text()):
        validator.validate(message)
    runtime=TrafficIntelligence('run.example',{'edge.market':10})
    output=runtime.tick(0,{})
    for name,rows in [('observation',output['observations']),('forecast',output['forecasts'])]:
        payload_validator=Draft202012Validator({'$defs':schema['$defs'],'$ref':f'#/$defs/{name}'})
        for row in rows:
            payload_validator.validate(row)
    scenario_schema=json.loads((root/'scenario.schema.json').read_text())
    Draft202012Validator.check_schema(scenario_schema)
    Draft202012Validator(scenario_schema).validate(json.loads((root/'rain-demo.example.json').read_text()))
