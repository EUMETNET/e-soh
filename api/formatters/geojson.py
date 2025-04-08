from fastapi import HTTPException
from geojson_pydantic import Feature
from geojson_pydantic import FeatureCollection
from geojson_pydantic import Point

from utilities import seconds_to_iso_8601_duration
from utilities import convert_cm_to_m


def _make_properties(ts):
    ts_metadata = {key.name: value for key, value in ts.ts_mdata.ListFields() if value and key.name != "links"}

    ts_metadata["platform_vocabulary"] = (
        "https://oscar.wmo.int/surface/rest/api/search/station?wigosId=" + ts.ts_mdata.platform
        if not ts.ts_mdata.platform_vocabulary
        else ts.ts_mdata.platform_vocabulary
    )

    ts_metadata["level"] = convert_cm_to_m(ts.ts_mdata.level)
    ts_metadata["period"] = seconds_to_iso_8601_duration(ts.ts_mdata.period)

    # TODO: Remove when return is 'method' instead of 'function'
    if "function" in ts_metadata:
        ts_metadata["method"] = ts_metadata.pop("function")

    if "platform_name" not in ts_metadata:
        ts_metadata["platform_name"] = f'platform-{ts_metadata["platform"]}'

    return ts_metadata


def convert_to_geojson(observations):
    """
    Will only generate geoJSON for stationary timeseries
    """
    features = [
        Feature(
            type="Feature",
            id=ts.ts_mdata.timeseries_id,
            properties=_make_properties(ts=ts),
            geometry=Point(
                type="Point",
                coordinates=[
                    ts.obs_mdata[0].geo_point.lon,
                    ts.obs_mdata[0].geo_point.lat,
                ],
            ),
        )
        for ts in sorted(observations, key=lambda ts: ts.ts_mdata.timeseries_id)
    ]
    if not features:
        raise HTTPException(404, detail="Query did not return any time series.")
    return FeatureCollection(features=features, type="FeatureCollection") if len(features) > 1 else features[0]
