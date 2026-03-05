import logging
from enum import Enum

from . import covjson
from . import geojson
from . import bufr

logger = logging.getLogger(__name__)


class Formats(str, Enum):
    covjson = "CoverageJSON"  # According to EDR spec


class Metadata_Formats(str, Enum):
    geojson = "GeoJSON"


formatters = {
    "CoverageJSON": covjson.convert_to_covjson,
    "bufr": bufr.convert_to_bufr,
}  # observations
metadata_formatters = {"GeoJSON": geojson.convert_to_geojson}  # metadata
