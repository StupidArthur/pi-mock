from dataclasses import asdict, dataclass
from typing import Optional

POINT_TYPES = {"Float32", "Float64", "Int16", "Int32", "Boolean", "String"}


@dataclass
class PointRecord:
    web_id: str
    name: str
    path: str
    descriptor: str = ""
    point_type: str = "Float32"
    engineering_units: str = ""
    zero: float = 0
    span: float = 100
    digital_set_name: Optional[str] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        return {
            "WebId": data["web_id"],
            "Name": data["name"],
            "Path": data["path"],
            "Descriptor": data["descriptor"],
            "PointType": data["point_type"],
            "EngineeringUnits": data["engineering_units"],
            "Zero": data["zero"],
            "Span": data["span"],
            "DigitalSetName": data["digital_set_name"],
        }


def build_path(server_name: str, name: str) -> str:
    return "\\\\" + server_name + "\\" + name


def normalize_path(path: str) -> str:
    if path is None:
        return ""
    text = str(path).strip().replace("/", "\\")
    text = text.strip("\\")
    return text.lower()
