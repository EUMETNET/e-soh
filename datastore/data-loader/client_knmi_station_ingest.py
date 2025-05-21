#!/usr/bin/env python3
# tested with Python 3.11
import math
import os
import requests
import random
import json
from multiprocessing import cpu_count, Pool
from pathlib import Path
from time import perf_counter
from typing import List
from typing import Tuple
from functools import partial

import pandas as pd
import xarray as xr
from google.protobuf.timestamp_pb2 import Timestamp
from parameters import knmi_parameter_names
from utilities import generate_parameter_name, convert_unit_names


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

                properties = {
                    "platform": platform,
                    "instrument": param_id,
                    "platform_name": station_name,
                    "title": param_file.long_name,
                    "Conventions": "CF-1.8",
                    "license": "CC BY 4.0",
                    "level": level,
                    "period": period,
                    "function": function,
                    "parameter_name": ":".join([standard_name, level, function, period]),
                    "naming_authority": "nl.knmi",
                    "keywords": file["iso_dataset"].attrs["keyword"],
                    "summary": file["iso_dataset"].attrs["abstract"],
                    "keywords_vocabulary": file.attrs["references"],
                    "source": file.attrs["source"],
                    "creator_name": "KNMI",
                    "creator_email": file["iso_dataset"].attrs["email_dataset"],
                    "creator_url": file["iso_dataset"].attrs["url_metadata"],
                    "creator_type": "institution",
                    "institution": file.attrs["institution"],
                    "hamsl": random.choice([1, 2, 3]),
                }

                geometry = {
                    "type": "Point",
                    "coordinates": {
                        "lon": longitude,
                        "lat": latitude,
                    },
                }

                for time, obs_value in zip(
                    pd.to_datetime(param_file["time"].data).to_pydatetime(),
                    param_file.data,
                ):

                    ts = Timestamp()
                    ts.FromDatetime(time)
                    if not math.isnan(obs_value):  # Stations that don't have a parameter give them all as nan
                        content = {
                            "encoding": "utf-8",
                            "standard_name": standard_name,
                            "unit": convert_unit_names(param_file.units),
                            "value": str(obs_value),
                        }

                        observations.append(
                            {
                                "properties": {
                                    **properties,
                                    "content": content,
                                    "datetime": ts.ToJsonString(),
                                },
                                "geometry": geometry,
                                "version": "4.0",
                                "type": "Feature",
                                "links": [
                                    {"href": "Insert documentation about E-SOH datastore", "rel": "canonical"},
                                ],
                            }
                        )

            if len(observations) > 0:
                observation_request_messages.append(observations)

    return observation_request_messages


def send_request_to_ingest(msg, url):
    try:
        response = requests.post(url, data=json.dumps(msg))
        response.raise_for_status()
        return response.status_code, response.json()
    except requests.RequestException as e:
        return response.status_code, e
    except Exception as e:
        return 500, e


def insert_data(observation_request_messages: List, url):
    print(f"Sending {len(observation_request_messages)} bulk observations requests to ingest.")
    obs_insert_start = perf_counter()

    partial_send_request = partial(send_request_to_ingest, url=url)

    with Pool(cpu_count()) as pool:
        results = pool.map(partial_send_request, observation_request_messages)

        for status_code, response in results:
            if status_code != 200:
                print(status_code, response)
                return
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
        url=os.getenv("INGEST_URL", "http://localhost:8009/json"),
    )

    print(f"Finished, total time elapsed: {perf_counter() - total_time_start}")


if __name__ == "__main__":
    main()
