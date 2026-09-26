from pydantic import BaseModel


class Software(BaseModel):
    software_id: str
    name: str
    version: str
    vendor: str
    asset_id: str