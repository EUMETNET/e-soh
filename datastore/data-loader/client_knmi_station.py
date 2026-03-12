#!/usr/bin/env python3
# tested with Python 3.11
import concurrent
import math
import os
import uuid

from hashlib import md5
from multiprocessing import cpu_count
from pathlib import Path
from time import perf_counter
from typing import List
from typing import Tuple

import datastore_pb2 as dstore
import datastore_pb2_grpc as dstore_grpc
import grpc
import pandas as pd
import xarray as xr
from google.protobuf.timestamp_pb2 import Timestamp
from parameters import knmi_parameter_names
from utilities import convert_unit_names, iso_8601_duration_to_seconds, generate_parameter_name


def netcdf_file_to_requests(file_path: Path | str) -> Tuple[List, List]:
    observation_request_messages = []

    with xr.open_dataset(file_path, engine="netcdf4", chunks=None) as file:  # chunks=None to disable dask
        for station_id, station_name, latitude, longitude, height in zip(
            file["station"].values,
            file["stationname"].values[0],
            file["lat"].values[0],
            file["lon"].values[0],
            file["height"].values[0],
        ):
            observations = []
            station_slice = file.sel(station=station_id)

            for param_id in knmi_parameter_names:
                param_file = station_slice[param_id]

                if "standard_name" in param_file.attrs:
                    standard_name, level, function, period = generate_parameter_name(
                        param_file.standard_name,
                        param_file.long_name,
                        station_id,
                        station_name,
                        param_id,
                    )
                else:
                    continue

                platform = f"0-20000-0-{station_id}"
                period_as_seconds = iso_8601_duration_to_seconds(period)
                level_as_centimeters = int(float(level) * 100)

                ts_mdata = dstore.TSMetadata(
                    platform=platform,
                    instrument=param_id,
                    platform_name=station_name,
                    title=param_file.long_name,
                    license="CC BY 4.0",
                    standard_name=standard_name,
                    unit=convert_unit_names(param_file.units) if "units" in param_file.attrs else None,
                    level=level_as_centimeters,
                    period=period_as_seconds,
                    function=function,
                    parameter_name=":".join([standard_name, str(float(level)), function, period]),
                    naming_authority="nl.knmi",
                    keywords=file["iso_dataset"].attrs["keyword"],
                    summary=file["iso_dataset"].attrs["abstract"],
                    keywords_vocabulary=file.attrs["references"],
                    source=file.attrs["source"],
                    creator_name="KNMI",
                    creator_email=file["iso_dataset"].attrs["email_dataset"],
                    creator_url=file["iso_dataset"].attrs["url_metadata"],
                    creator_type="institution",
                    institution=file.attrs["institution"],
                    timeseries_id=md5(
                        "".join(
                            [
                                "nl.knmi",
                                platform,
                                standard_name,
                                str(level_as_centimeters),
                                function,
                                str(period_as_seconds),
                            ]
                        ).encode()
                    ).hexdigest(),
                )

                for time, obs_value in zip(
                    pd.to_datetime(param_file["time"].data).to_pydatetime(),
                    param_file.data,
                ):
                    ts = Timestamp()
                    ts.FromDatetime(time)
                    if not math.isnan(obs_value):  # Stations that don't have a parameter give them all as nan
                        obs_mdata = dstore.ObsMetadata(
                            id=str(uuid.uuid4()),
                            geo_point=dstore.Point(lat=latitude, lon=longitude),
                            obstime_instant=ts,
                            camsl=int(float(height) * 100),  # Store height as centimeters in camsl field
                            value=str(obs_value),  # TODO: Store float in DB
                        )
                        observations.append(dstore.Metadata1(ts_mdata=ts_mdata, obs_mdata=obs_mdata))

            if len(observations) > 0:
                observation_request_messages.append(dstore.PutObsRequest(observations=observations))

    return observation_request_messages


def insert_data(observation_request_messages: List):
    workers = int(cpu_count())

    with grpc.insecure_channel(f"{os.getenv('DSHOST', 'localhost')}:{os.getenv('DSPORT', '50050')}") as channel:
        client = dstore_grpc.DatastoreStub(channel=channel)

        print(f"Inserting {len(observation_request_messages)} bulk observations requests.")
        obs_insert_start = perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            for _ in executor.map(client.PutObservations, observation_request_messages):
                pass
        print(f"Finished observations bulk insert {perf_counter() - obs_insert_start}.")


def main():
    total_time_start = perf_counter()

    print("Starting with creating the time series and observations requests.")
    create_requests_start = perf_counter()
    file_path = Path(Path(__file__).parent / "test-data" / "KNMI" / "20221231.nc")
    observation_request_messages = netcdf_file_to_requests(file_path=file_path)
    print("Finished creating the time series and observation requests " f"{perf_counter() - create_requests_start}.")

    insert_data(
        observation_request_messages=observation_request_messages,
    )

    print(f"Finished, total time elapsed: {perf_counter() - total_time_start}")


if __name__ == "__main__":
    main()
