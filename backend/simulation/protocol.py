"""Versioned public protocol. Frozen v1 phone messages remain unchanged."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Command(BaseModel):
    model_config=ConfigDict(extra='forbid')
    api_version: Literal['2.0']='2.0'
    command_id: str=Field(min_length=1,max_length=128)
    run_id: str=Field(min_length=1,max_length=128)
    expected_revision: int=Field(ge=0)
    payload: dict

class Login(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username: str=Field(min_length=1,max_length=128)
    password: str=Field(min_length=1,max_length=256)

class Lease(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action: Literal['acquire','renew','release']='acquire'
    takeover: bool=False

class Registration(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username: str=Field(min_length=3,max_length=32)
    password: str=Field(min_length=8,max_length=256)
    request_operator: bool=True

class Approval(BaseModel):
    model_config=ConfigDict(extra='forbid')
