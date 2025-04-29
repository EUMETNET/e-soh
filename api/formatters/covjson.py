import math
import operator
from collections import namedtuple
from datetime import timezone
from functools import reduce
from itertools import groupby

from covjson_pydantic.coverage import Coverage
from covjson_pydantic.coverage import CoverageCollection
from covjson_pydantic.domain import Axes
from covjson_pydantic.domain import Domain
from covjson_pydantic.domain import DomainType
from covjson_pydantic.domain import ValuesAxis
from covjson_pydantic.ndarray import NdArrayFloat
from covjson_pydantic.observed_property import ObservedProperty
from covjson_pydantic.parameter import Parameter
from covjson_pydantic.reference_system import ReferenceSystem
from covjson_pydantic.reference_system import ReferenceSystemConnectionObject
from edr_pydantic.parameter import MeasurementType
from covjson_pydantic.unit import Unit
from fastapi import HTTPException
from pydantic import AwareDatetime

from utilities import seconds_to_iso_8601_duration, convert_cm_to_m

# mime_type = "application/prs.coverage+json"

Dom = namedtuple("Dom", ["lat", "lon", "times"])
Data = namedtuple("Data", ["dom", "values", "ts_mdata"])


def make_parameter(ts_mdata):
    level = convert_cm_to_m(ts_mdata.level)
    period = seconds_to_iso_8601_duration(ts_mdata.period)
    label = " ".join(ts_mdata.standard_name.capitalize().split("_"))

    custom_fields = {
        "rodeo:standard_name": ts_mdata.standard_name,
        "rodeo:level": level,
    }

    return Parameter(
        description={
            "en": f"{label} at {level}m, aggregated over {period} with method '{ts_mdata.function}'",
        },
        observedProperty=ObservedProperty(
            id=f"https://vocab.nerc.ac.uk/standard_name/{ts_mdata.standard_name}",
            label={"en": label},
        ),
        measurementType=MeasurementType(
            method=ts_mdata.function,
            duration=period,
        ),
        unit=Unit(label={"en": ts_mdata.unit}),
        **custom_fields,
    )


def convert_to_covjson(observations):
    # Collect data
    coverages = []
    data = [_collect_data(md.ts_mdata, md.obs_mdata) for md in observations]

    # Need to sort before using groupBy. Also sort on parameter_name to get consistently sorted output
    data.sort(key=lambda x: (x.dom, x.ts_mdata.parameter_name))
    for (lat, lon, times), group in groupby(data, lambda x: x.dom):
        referencing = [
            ReferenceSystemConnectionObject(
                coordinates=["y", "x"],
                system=ReferenceSystem(type="GeographicCRS", id="http://www.opengis.net/def/crs/EPSG/0/4326"),
            ),
            ReferenceSystemConnectionObject(
                coordinates=["t"],
                system=ReferenceSystem(type="TemporalRS", calendar="Gregorian"),
            ),
        ]
        domain = Domain(
            domainType=DomainType.point_series,
            axes=Axes(
                x=ValuesAxis[float](values=[lon]),
                y=ValuesAxis[float](values=[lat]),
                t=ValuesAxis[AwareDatetime](values=times),
            ),
            referencing=referencing,
        )

        parameters = {}
        ranges = {}
        for data in group:
            if all(math.isnan(v) for v in data.values):
                continue  # Drop ranges if completely nan.
                # TODO: Drop the whole coverage if it becomes empty?
            values_no_nan = [v if not math.isnan(v) else None for v in data.values]

            parameter_id = data.ts_mdata.parameter_name
            parameters[parameter_id] = make_parameter(data.ts_mdata)

            ranges[parameter_id] = NdArrayFloat(
                values=values_no_nan, axisNames=["t", "y", "x"], shape=[len(values_no_nan), 1, 1]
            )

        custom_fields = {"rodeo:wigosId": data.ts_mdata.platform}
        coverages.append(Coverage(domain=domain, parameters=parameters, ranges=ranges, **custom_fields))

    if len(coverages) == 0:
        raise HTTPException(status_code=404, detail="Requested data not found.")
    elif len(coverages) == 1:
        return coverages[0]
    else:
        parameter_union = reduce(operator.ior, (c.parameters for c in coverages), {})
        return CoverageCollection(coverages=coverages, parameters=dict(sorted(parameter_union.items())))


def _collect_data(ts_mdata, obs_mdata):
    lat = obs_mdata[0].geo_point.lat  # HACK: For now assume they all have the same position
    lon = obs_mdata[0].geo_point.lon
    tuples = (
        (o.obstime_instant.ToDatetime(tzinfo=timezone.utc), float(o.value)) for o in obs_mdata
    )  # HACK: str -> float
    (times, values) = zip(*tuples)

    return Data(Dom(lat, lon, times), values, ts_mdata)
