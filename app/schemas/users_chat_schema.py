from pydantic import BaseModel
from typing import Optional
from enum import Enum

class OutputFormat(str , Enum):
    excel = "excel"
    bdd = "bdd"

class UserChatBase(BaseModel):
    requirements : Optional[str] = None


class UserMessageBase(BaseModel):
    message : str

class UserChatUpdateBase(BaseModel):
    title : Optional[str] = None
    requirements : Optional[str] = None