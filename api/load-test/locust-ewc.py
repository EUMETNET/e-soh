from datetime import datetime, timedelta, UTC
import random

from locust import HttpUser
from locust import task

headers = {"Accept-Encoding": "br"}

common_standard_names = [
    "wind_speed",
    "wind_from_direction",
    "air_temperature",
]

polygon_size = [0.5, 1.0, 2.0, 4.0]
hours_choice = [1, 3, 6, 12, 24]


class ESohUser(HttpUser):
    def on_start(self):
        response = self.client.get("/collections/observations/locations", headers=headers)
        stations = response.json()["features"]
        self.stations = {s["id"]: s["properties"]["parameter-name"] for s in stations}
        self.station_ids = list(self.stations.keys())
        self.stations_by_location = {
            (s["geometry"]["coordinates"][0], s["geometry"]["coordinates"][1]): s["properties"]["parameter-name"]
            for s in stations
        }
        self.station_locations = list(self.stations_by_location.keys())

    # @task
    # def get_data_single_station_single_parameter(self):
    #     station_id = random.choice(self.station_ids)
    #     parameter = random.choice(self.stations[station_id])
    #     response = self.client.get(
    #         f"/collections/observations/locations/{station_id}?parameter-name={parameter}",
    #         name="location",
    #         headers=headers
    #     )

    @task
    def get_data_single_station_single_parameter_last_x_hours(self):
        hours = random.choice(hours_choice)
        date_time = datetime.now(UTC) - timedelta(hours=hours)
        dt_string = date_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        station_id = random.choice(self.station_ids)
        parameter = random.choice(self.stations[station_id])
        self.client.get(
            f"/collections/observations/locations/{station_id}?parameter-name={parameter}&datetime={dt_string}/..",
            name=f"location {hours:02d} hours",
            headers=headers,
        )

    @task
    def get_data_single_position_single_parameter(self):
        (lon, lat) = random.choice(self.station_locations)
        parameter = random.choice(self.stations_by_location[(lon, lat)])
        self.client.get(
            f"/collections/observations/position?coords=POINT({lon} {lat})&parameter-name={parameter}",
            name="position",
            headers=headers,
        )

    @task
    def get_data_area_single_parameter_last_hour(self):
        date_time = datetime.now(UTC) - timedelta(hours=1)
        dt_string = date_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        standard_name = random.choice(common_standard_names)
        (cx, cy) = random.choice(self.station_locations)
        sz = random.choice(polygon_size) / 2.0
        left = cx - sz
        bottom = cy - sz
        right = cx + sz
        top = cy + sz
        polygon = f"POLYGON(({left} {bottom},{right} {bottom},{right} {top},{left} {top},{left} {bottom}))"
        url = f"/collections/observations/area?coords={polygon}&standard_names={standard_name}&datetime={dt_string}/.."
        self.client.get(url, name=f"area {sz * 2.0}deg x {sz * 2.0}deg x 1h", headers=headers)
        # if sz == 2.0:
        #     j = response.json()
        #     # print(sz*2.0)
        #     if response.status_code != 200:
        #         print(0)
        #     elif j["type"] == "CoverageCollection":
        #         print(len(j["coverages"]))
        #     else:
        #         print(1)
        # # print(j)
