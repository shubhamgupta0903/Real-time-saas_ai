from pydantic import BaseModel
from typing import Dict

class Component(BaseModel):
    name: str
    type: str  # e.g., "chart", "table", "KPI"
    config: Dict  # Configuration settings
    pinned: bool = False  # New field for pinning components

class User(BaseModel):
    username: str
    password: str
