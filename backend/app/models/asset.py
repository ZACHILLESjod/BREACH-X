from pydantic import BaseModel
from typing import Optional


class Asset(BaseModel):
    asset_id: str
    hostname: str
    ip_address: str
    asset_type: str
    operating_system: Optional[str] = None
    criticality: str = "medium"