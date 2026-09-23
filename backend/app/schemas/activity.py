from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ActivityResponse(BaseModel):
    id: str
    project_id: Optional[str] = None
    entity_type: str
    entity_id: Optional[str] = None
    action: str
    description: str
    user: str
    details: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
