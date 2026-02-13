from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from api.model import Link

import datetime as pkg_datetime
import hashlib
from typing import Annotated

from pydantic import UUID4
from pydantic import PlainSerializer
from pydantic import model_validator
from geojson_pydantic import Point


def serialize_timestamp(dt: pkg_datetime.datetime | pkg_datetime.date) -> str:
    """Serialize a datetime object to ISO 8601 string format."""
    if isinstance(dt, pkg_datetime.datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pkg_datetime.timezone.utc)
        else:
            dt = dt.astimezone(pkg_datetime.timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif isinstance(dt, pkg_datetime.date):
        return dt.strftime("%Y-%m-%d")
    else:
        raise TypeError("Input must be a datetime or date object")


class Content(BaseModel):
    encoding: Literal["utf-8", "base64", "gzip"] = Field(..., description="Encoding of content")
    size: int | None = Field(
        None,
        description=(
            "Number of bytes contained in the file. Together with the ``integrity`` property,"
            " it provides additional assurance that file content was accurately received."
            "Note that the limit takes into account the data encoding used, "
            "including data compression (for example `gzip`)."
        ),
        le=4096,
    )
    value: str = Field(..., description="The inline content of the file. Max size is 4096 bytes.")
    unit: str = Field(..., description="Unit for the data")

    @model_validator(mode="after")
    def check_size_of_content(self):
        if (file_size := len(self.value)) > 4096:
            raise ValueError(f"Size of message content too large: {file_size} > 4096. Use /upload instead.")
        return self

    class Config:
        str_strip_whitespace = True


class Integrity(BaseModel):
    method: Literal["sha256", "sha384", "sha512", "sha3-256", "sha3-384", "sha3-512"]
    value: str = Field(..., desciption="The hash value for the value field in the message content.")


class Properties(BaseModel):
    datetime: Annotated[pkg_datetime.datetime | pkg_datetime.date | None, PlainSerializer(serialize_timestamp)] = Field(
        None,
        description="Identifies the date/time of the data being recorded, in RFC3339 format.",
    )
    producer: Optional[str] = Field(
        None,
        description="Identifies the provider that initially captured and processed the source data,"
        " in support of data distribution on behalf of other Members",
    )
    data_id: str = Field(
        ...,
        description="Unique identifier of the data as defined by the data producer.",
    )
    start_datetime: Optional[pkg_datetime.datetime] = Field(
        None,
        description="Identifies the start date/time date of the data being recorded, in RFC3339 format.",
    )
    end_datetime: Optional[pkg_datetime.datetime] = Field(
        None,
        description="Identifies the end date/time date of the data being recorded, in RFC3339 format.",
    )
    metadata_id: Optional[str] = Field(
        ...,
        description="Identifier for associated discovery metadata record to which the notification applies",
    )
    content: Optional[Content] = Field(None, description="Actual data content.")
    integrity: Optional[Integrity] = Field(None, exclude_from_schema=True)

    @model_validator(mode="after")
    def set_dateimte(self):
        assert bool(self.datetime) != bool(self.start_datetime and self.end_datetime), (
            "Set datetime or start_datetime and end_datetime. At least one and not both. "
            + f"{self.datetime}, {self.start_datetime} - {self.end_datetime}"
        )
        return self

    @model_validator(mode="after")
    def calc_integrity(self):
        if self.content:  # If content is set, calculate the integrity check.
            self.integrity = Integrity(method="sha256", value=hashlib.sha256(self.content.value.encode()).hexdigest())
        return self


class PropertiesWIS2(Properties):
    pubtime: Annotated[pkg_datetime.datetime | pkg_datetime.date, PlainSerializer(serialize_timestamp)] = Field(
        ...,
        description="Identifies the date/time of the message being published, in RFC3339 format.",
    )
    integrity: Optional[Integrity] = Field(
        None,
        description="Specifies a checksum to be applied to the data to ensure that the download is accurate.",
    )


class Wis2MessageSchema(BaseModel):
    id: UUID4
    type: Literal["Feature"] = "Feature"
    conformsTo: Literal["http://wis.wmo.int/spec/wnm/1/conf/core"] = "http://wis.wmo.int/spec/wnm/1/conf/core"
    geometry: Point
    properties: PropertiesWIS2
    links: List[Link] = Field(..., min_length=1)
