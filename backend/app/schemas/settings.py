from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class UserSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sensitivity_tolerance: float
    api_key: str
    version: int
    updated_at: datetime

class UserSettingsUpdate(BaseModel):
    sensitivity_tolerance: Optional[float] = None
    api_key: Optional[str] = None
    version: Optional[int] = None
