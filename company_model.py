from dataclasses import dataclass, asdict
from typing import Optional
import json


@dataclass
class CompanyModel:
    name: str
    address: str
    website: str
    category: str
    phone: Optional[str] = None
    email: Optional[str] = None

    def __repr__(self) -> str:
        return json.dumps(asdict(self), indent=4)

    def as_dict(self):
        return asdict(self)
