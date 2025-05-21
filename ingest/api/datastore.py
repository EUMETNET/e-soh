import logging

from datetime import datetime
from dateutil import parser

from api.utilities import convert_to_meter
from api.utilities import seconds_to_iso_8601_duration


import datastore_pb2 as dstore

from google.protobuf.timestamp_pb2 import Timestamp

logger = logging.getLogger(__name__)


def dtime2tstamp(dtime):
    tstamp = Timestamp()
    tstamp.FromDatetime(dtime)
    return tstamp


def build_grpc_messages(msg: str) -> None:
    """
    This method sets up required fields in TSMetadata, ObsMetadata and ingest data to datastore
    """
    ts_metadata = dstore.TSMetadata()
    field_list_ts = ts_metadata.DESCRIPTOR.fields_by_name.keys()
    for i in field_list_ts:
        if i in msg["properties"]:
            setattr(ts_metadata, i, msg["properties"][i])
        elif i in msg["properties"]["content"]:
            setattr(ts_metadata, i, msg["properties"]["content"][i])

    level = str(ts_metadata.level)
    period = str(ts_metadata.period)
    function = ts_metadata.function
    standard_name = ts_metadata.standard_name
    parameter_name = ":".join(
        [
            standard_name,
            convert_to_meter(level),
            function,
            seconds_to_iso_8601_duration(int(period)),
        ]
    )
    setattr(ts_metadata, "parameter_name", parameter_name)

    observation_data = dstore.ObsMetadata()
    field_list_obs = observation_data.DESCRIPTOR.fields_by_name.keys()

    for i in field_list_obs:
        if i == "obstime_instant":
            if "datetime" in msg["properties"]:
                obstime_instant = dtime2tstamp(parser.isoparse(msg["properties"]["datetime"]))
                observation_data.obstime_instant.CopyFrom(obstime_instant)
        elif i in msg:
            setattr(observation_data, i, msg[i])
        elif i in msg["properties"]:
            if i == "pubtime":
                pubtime = dtime2tstamp(datetime.strptime(msg["properties"]["pubtime"], "%Y-%m-%dT%H:%M:%S%z"))
                observation_data.pubtime.CopyFrom(pubtime)
            else:
                setattr(observation_data, i, msg["properties"][i])
        elif i in msg["properties"]["content"]:
            setattr(observation_data, i, msg["properties"]["content"][i])

    if "geometry" in msg:
        if msg["geometry"]["type"] == "Point":
            point = dstore.Point(
                lat=float(msg["geometry"]["coordinates"]["lat"]),
                lon=float(msg["geometry"]["coordinates"]["lon"]),
            )
            observation_data.geo_point.CopyFrom(point)

    return dstore.Metadata1(ts_mdata=ts_metadata, obs_mdata=observation_data)
