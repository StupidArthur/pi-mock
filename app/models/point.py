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

    def links(self, server_web_id: str) -> dict:
        return {
            "Self": "/piwebapi/points/" + self.web_id,
            "DataServer": "/piwebapi/dataservers/" + server_web_id,
            "Value": "/piwebapi/streams/" + self.web_id + "/value",
            "RecordedData": "/piwebapi/streams/" + self.web_id + "/recorded",
        }

    def to_dict(self, server_web_id: Optional[str] = None) -> dict:
        data = asdict(self)
        result = {
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
        if server_web_id:
            result["Links"] = self.links(server_web_id)
        return result

    def to_summary_dict(self) -> dict:
        return {"WebId": self.web_id, "Name": self.name, "Path": self.path}


def build_path(server_name: str, name: str) -> str:
    return "\\\\" + server_name + "\\" + name


def normalize_path(path: str) -> str:
    if path is None:
        return ""
    text = str(path).strip().replace("/", "\\")
    text = text.strip("\\")
    return text.lower()
