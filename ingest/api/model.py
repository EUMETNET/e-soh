import json
import isodate

from pydantic.functional_validators import field_validator

from typing import List
from typing import Literal
from typing import Optional
from dateutil import parser
from datetime import timedelta
from isodate import ISO8601Error

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


with open("api/cf_standard_names_v84.txt", "r") as file:
    standard_names = {line.strip() for line in file}

with open("api/cf_standard_names_alias_v84.txt", "r") as file:
    standard_names_alias = {}
    for i in file:
        i = i.strip().split(":")
        standard_names_alias[i[1]] = i[0]

with open("api/std_name_units.json") as f:
    std_name_unit_mapping = json.load(f)


class Coordinate(BaseModel):
    lat: float
    lon: float


class Geometry(BaseModel):
    type: Literal["Point"]
    coordinates: Coordinate


class Integrity(BaseModel):
    method: Literal["sha256", "sha384", "sha512", "sha3-256", "sha3-384", "sha3-512"] = Field(
        ...,
        description="A specific set of methods for calculating the checksum algorithms",
    )
    value: str = Field(..., description="Checksum value.")


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
    )
    value: str = Field(..., description="The inline content of the file.")
    standard_name: str = Field(..., description="CF standard for the data included in this message.")
    unit: str = Field(..., description="Unit for the data")

    @model_validator(mode="after")
    def check_standard_name_match(self):
        if self.standard_name in standard_names_alias:
            self.standard_name = standard_names_alias[self.standard_name]

        if self.standard_name not in standard_names:
            raise ValueError(f"{self.standard_name} is not a CF Standard name")
        return self

    @model_validator(mode="after")
    def standardize_units(self):
        if self.unit == std_name_unit_mapping[self.standard_name]["unit"]:
            return self
        elif (
            "alias" in std_name_unit_mapping[self.standard_name]
            and self.unit in std_name_unit_mapping[self.standard_name]["alias"]
        ):
            self.unit = std_name_unit_mapping[self.standard_name]["unit"]
        elif "conversion" in std_name_unit_mapping[self.standard_name] and self.unit in (
            conversion := std_name_unit_mapping[self.standard_name]["conversion"]
        ):
            number_of_decimals = len(self.value.split(".")[1]) if len(self.value.split(".")) == 2 else 0
            tmp_value = (float(self.value) + conversion[self.unit].get("add", 0)) * conversion[self.unit].get("mul", 1)
            self.value = f"{tmp_value:.{number_of_decimals}f}"
            self.unit = std_name_unit_mapping[self.standard_name]["unit"]
            return self
        else:
            raise ValueError(
                f"Unknown unit or unit alias for {self.standard_name}. Provided unit {self.unit} is unknown."
            )

        return self

    class Config:
        str_strip_whitespace = True


class Properties(BaseModel):
    title: Optional[str] = Field(
        None,
        description=(
            "short phrase or sentence describing the dataset. In many discovery systems, "
            "the title will be displayed in the results list from a search, "
            "and therefore should be human readable and reasonable to display in a list of such names."
            " This attribute is also recommended by the NetCDF Users Guide and the CF conventions."
        ),
    )
    summary: str = Field(
        ...,
        description="A paragraph describing the dataset, analogous to an abstract for a paper.",
    )
    keywords: Optional[str] = Field(
        None,
        description=(
            "A comma-separated list of key words and/or phrases. Keywords may be common words or phrases, "
            "terms from a controlled vocabulary (GCMD is often used),"
            "or URIs for terms from a controlled vocabulary (see also 'keywords_vocabulary' attribute)."
        ),
    )
    keywords_vocabulary: Optional[str] = Field(
        None,
        description=(
            "If you are using a controlled vocabulary for the words/phrases in your 'keywords' attribute,"
            " this is the unique name or identifier of the vocabulary from which keywords are taken. "
            "If more than one keyword vocabulary is used, each may be presented with a prefix and a following comma, "
            "so that keywords may optionally be prefixed with the controlled vocabulary key."
        ),
    )
    license: str = Field(
        ...,
        description=(
            "Provide the URL to a standard or specific license, enter 'Freely Distributed' or 'None', "
            "or describe any restrictions to data access and distribution in free text."
        ),
    )
    Conventions: str = Field(
        ...,
        description=(
            "A comma-separated list of the conventions that are followed by the dataset."
            " For files that follow this version of ACDD, "
            "include the string 'ACDD-1.3'. (This attribute is described in the NetCDF Users Guide.)"
        ),
    )
    naming_authority: str = Field(
        ...,
        description=(
            "The organization that provides the initial id (see above) for the dataset."
            " The naming authority should be uniquely specified by this attribute."
            " We recommend using reverse-DNS naming for the naming authority; "
            "URIs are also acceptable. Example: 'edu.ucar.unidata'."
        ),
    )
    creator_type: Optional[Literal["person", "group", "institution", "position"]] = Field(
        None,
        description=(
            "Specifies type of creator with one of the following: 'person', 'group', 'institution', or 'position'. "
            "If this attribute is not specified, the creator is assumed to be a person."
        ),
    )
    creator_name: Optional[str] = Field(
        None,
        description=(
            "The name of the person (or other creator type specified by the creator_type attribute) "
            "principally responsible for creating this data."
        ),
    )
    creator_email: Optional[str] = Field(
        None,
        description=(
            "The email address of the person (or other creator type specified by the creator_type attribute) "
            "principally responsible for creating this data."
        ),
    )
    creator_url: Optional[str] = Field(
        None,
        description=(
            "The URL of the person (or other creator type specified by the creator_type attribute) principally "
            "responsible for creating this data."
        ),
    )
    institution: Optional[str] = Field(
        None,
        description=(
            "The name of the institution principally responsible for originating this data. "
            "This attribute is recommended by the CF convention."
        ),
    )
    project: Optional[str] = Field(
        None,
        description=(
            "The name of the project(s) principally responsible for originating this data."
            " Multiple projects can be separated by commas, as described under Attribute Content Guidelines. "
            "Examples: 'PATMOS-X', 'Extended Continental Shelf Project'."
        ),
    )
    source: Optional[str] = Field(
        None,
        description=(
            "The method of production of the original data. If it was model-generated,"
            " source should name the model and its version. "
            "If it is observational, source should characterize it. This attribute is defined in the CF Conventions."
        ),
    )
    platform: str = Field(
        ...,
        description=(
            "WIGOS-ID of the platform(s) that supported the sensor data used to create this data set or product. "
            "Platforms can be of any type, including satellite, ship, station, aircraft or other. "
            "Indicate controlled vocabulary used in platform_vocabulary."
        ),
    )
    platform_name: Optional[str] = Field(None, description=("Human readable name for the platform."))
    platform_vocabulary: Optional[str] = Field(
        None,
        description="Controlled vocabulary for the names used in the 'platform' attribute.",
    )
    instrument: Optional[str] = Field(
        None,
        description=(
            "Name of the contributing instrument(s) or sensor(s) used to create this data set or product. "
            "Indicate controlled vocabulary used in instrument_vocabulary."
        ),
    )
    instrument_vocabulary: Optional[str] = Field(
        None,
        description="Controlled vocabulary for the names used in the 'instrument' attribute.",
    )
    level: str | int | float = Field(
        ...,
        description=("Instrument level above ground in meters."),
    )
    period: str = Field(
        ...,
        description=(
            "Aggregation period for the measurement. Must be provided in ISO8601 duration format."
            "https://www.iso.org/iso-8601-date-and-time-format.html"
        ),
    )
    period_int: int = Field(None, exclude_from_schema=True)
    function: Literal[
        "point",
        "sum",
        "maximum",
        "maximum_absolute_value",
        "median",
        "mid_range",
        "minimum",
        "minimum_absolute_value",
        "mean",
        "mean_absolute_value",
        "mode",
        "root_mean_square",
        "variance",
    ] = Field(
        ...,
        description=(
            "Function used on the data during the aggregation period."
            "Must be one of the functions given in CF cell_methods table."
            "https://cfconventions.org/Data/cf-conventions/cf-conventions-1.7/build/ape.html"
        ),
    )
    history: Optional[str] = Field(
        None,
        description=(
            "Provides an audit trail for modifications to the original data. "
            "This attribute is also in the NetCDF Users Guide: 'This is a character array with a line for each "
            "invocation of a program that has modified the dataset. "
            "Well-behaved generic netCDF applications should append a line containing: date, time of day, user name, "
            "program name and command arguments.' To include a more complete description you can append a reference to"
            " an ISO Lineage entity; see NOAA EDM ISO Lineage guidance."
        ),
    )
    datetime: str = Field(
        ...,
        description="Identifies the date/time of the datas being published, in RFC3339 format.",
    )
    start_datetime: Optional[str] = Field(
        None,
        description="Identifies the start date/time date of the data being published, in RFC3339 format.",
    )
    end_datetime: Optional[str] = Field(
        None,
        description="Identifies the end date/time date of the data being published, in RFC3339 format.",
    )
    processing_level: Optional[str] = Field(
        None,
        description="A textual description of the processing (or quality control) level of the data.",
    )
    quality_code: Optional[int] = Field(
        None,
        description=("The quality of the data. " "Indicate controlled vocabulary used in quality_code_vocabulary."),
    )
    quality_code_vocabulary: Optional[str] = Field(
        None,
        description="Controlled vocabulary for the values used in the 'quality_code' attribute.",
    )
    hamsl: Optional[int | float] = Field(
        None,
        description=(
            "The number of meters above mean sea level. "
            "The reference point is the ground position of the station for stationary data, or "
            "the sensor itself for mobile data."
        ),
    )
    content: Content = Field(..., description="Actual data content")
    integrity: Optional[Integrity] = Field(
        None,
        description="Specifies a checksum to be applied to the data to ensure that the download is accurate.",
    )

    @field_validator("hamsl", mode="before")
    @classmethod
    def convert_hamsl_to_centimeters(cls, hamsl: float):
        return int(hamsl * 100)

    @field_validator("period", mode="before")
    @classmethod
    def capitalize_period(cls, period: str):
        if isinstance(period, str):
            return period.upper()
        return period

    @model_validator(mode="after")
    def convert_to_cm(self):
        self.level = int(float(self.level) * 100)
        return self

    @model_validator(mode="after")
    def check_datetime_iso(self) -> "Properties":
        try:
            dt = parser.isoparse(self.datetime)
        except ValueError:
            raise ValueError(f"{self.datetime} not in ISO format(YYYY-MM-DDTHH:MM:SSZ)")
        except Exception as e:
            raise e

        if dt.tzname() != "UTC":
            raise ValueError(f"Input datetime, {self.datetime}, is not in UTC timezone")
        return self

    @model_validator(mode="after")
    def validate_wigos_id(self):
        blocks = self.platform.split("-")
        assert len(blocks) == 4, f"Not enough blocks in input 'platform', '{self.platform}'"
        for i in blocks[:-1]:
            assert (
                i.isdigit() and 0 <= int(i) <= 65534
            ), f"In input 'platform', '{self.platform}', one of  4 blocks is not a valid numerical or out of range."

        assert 0 < len(blocks[-1]) <= 16, f"In input 'platform', '{self.platform}', last block of WIGOS is to long"

        return self

    @model_validator(mode="after")
    def transform_period_to_seconds(self):
        try:
            duration = isodate.parse_duration(self.period)
        except ISO8601Error:
            raise ValueError(f"Invalid ISO 8601 duration: {self.period}")
        if isinstance(duration, timedelta):
            # It's a simple timedelta, so just get the total seconds
            total_seconds = duration.total_seconds()

        else:
            raise ValueError("Duration not convertable to seconds.")

        self.period_int = int(total_seconds)
        return self


class Link(BaseModel):
    href: str = Field(..., examples=["http://data.example.com/buildings/123"])
    rel: str = Field(..., examples=["alternate"])
    type: Optional[str] = Field(None, examples=["application/geo+json"])
    hreflang: Optional[str] = Field(None, examples=["en"])
    title: Optional[str] = Field(None, examples=["Trierer Strasse 70, 53115 Bonn"])
    length: Optional[int] = None


class JsonMessageSchema(BaseModel):
    type: Literal["Feature"]
    geometry: Geometry
    properties: Properties
    links: List[Link] = Field(..., min_length=1)
    version: str

    def __hash__(self):
        return hash(
            (
                self.properties.level,
                self.properties.platform,
                self.properties.content.standard_name,
                self.properties.period,
                self.properties.naming_authority,
                self.properties.function,
                self.properties.datetime,
            )
        )
