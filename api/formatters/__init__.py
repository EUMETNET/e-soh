import logging
from enum import Enum

from . import covjson
from . import geojson
from . import bufr

logger = logging.getLogger(__name__)


class Formats(str, Enum):
    covjson = "CoverageJSON"  # According to EDR spec
    bufr = "bufr"


class Metadata_Formats(str, Enum):
    geojson = "GeoJSON"


formatters = {
    "CoverageJSON": {
        "format_function": covjson.convert_to_covjson,
        "response_format": "application/prs.coverage+json",
    },
    "bufr": {
        "format_function": bufr.convert_to_bufr,
        "response_format": "application/bufr",
    },
}  # observations
metadata_formatters = {"GeoJSON": geojson.convert_to_geojson}  # metadata
