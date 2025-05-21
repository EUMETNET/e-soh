from datetime import datetime, UTC
import random
import logging
from dateutil.relativedelta import relativedelta  # From python-dateutil

from locust import HttpUser
from locust import task


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


scenarios = [
    # (delta, n_parameters)
    # None means all
    (relativedelta(hours=2), None),
    (relativedelta(hours=6), None),
    (relativedelta(hours=24), 5),
]

polygon_size = [0.5, 1.0, 2.0]


def human_readable(delta):
    attrs = ["years", "months", "days", "hours", "minutes", "seconds"]
    return [
        "%d %s" % (getattr(delta, attr), attr if getattr(delta, attr) > 1 else attr[:-1])
        for attr in attrs
        if getattr(delta, attr)
    ]


class ESohUser(HttpUser):
    def on_start(self):
        response = self.client.get("/collections/observations/locations", headers=self.headers)
        stations = response.json()["features"]
        self.stations = {s["id"]: s["properties"]["parameter-name"] for s in stations}
        self.station_ids = list(self.stations.keys())
        self.stations_by_location = {
            (s["geometry"]["coordinates"][0], s["geometry"]["coordinates"][1]): s["properties"]["parameter-name"]
            for s in stations
        }
        self.station_locations = list(self.stations_by_location.keys())

    def generate_random_input(self, parameters, interval: relativedelta, n_parameters):
        end = datetime.now(UTC)
        start = end - interval

        params = {
            "datetime": start.strftime("%Y-%m-%dT%H:%M:%SZ") + "/..",
        }
        if n_parameters:
            try:
                params["parameter-name"] = ",".join(random.sample(parameters, n_parameters))
            except ValueError:
                params["parameter-name"] = parameters
        return params

    headers = {"Accept-Encoding": "br"}

    @task
    def test_locations_data(self):
        scenario = random.choice(scenarios)
        station_id = random.choice(self.station_ids)
        params = self.generate_random_input(self.stations[station_id], *scenario)
        # print(params)

        name = f"/locations period: {human_readable(scenario[0])}, variables: {scenario[1]}"

        response = self.client.get(
            name=name, url=f"/collections/observations/locations/{station_id}", params=params, headers=self.headers
        )
        if response.status_code != 200:
            logger.info(params)
            logger.info(
                f"Response status code: {response.status_code}; Scenario {name} Response body: {response.text};"
            )

    @task
    def test_position(self):
        (lon, lat) = random.choice(self.station_locations)
        scenario = random.choice(scenarios)
        params = self.generate_random_input(self.stations_by_location[(lon, lat)], *scenario)
        params["coords"] = f"POINT({lon} {lat})"
        # print(params)

        name = f"/position period: {human_readable(scenario[0])}, variables: {scenario[1]}"

        response = self.client.get(
            name=name, url="/collections/observations/position", params=params, headers=self.headers
        )
        if response.status_code != 200:
            logger.info(params)
            logger.info(
                f"Response status code: {response.status_code}; Scenario {name} Response body: {response.text};"
            )

    @task
    def test_area(self):
        scenario = random.choice(scenarios)
        (cx, cy) = random.choice(self.station_locations)
        sz = random.choice(polygon_size) / 2.0
        left = cx - sz
        bottom = cy - sz
        right = cx + sz
        top = cy + sz

        params = self.generate_random_input(self.stations_by_location[(cx, cy)], *scenario)
        params["coords"] = f"POLYGON(({left} {bottom},{right} {bottom},{right} {top},{left} {top},{left} {bottom}))"
        # print(params)

        name = f"/area size: {sz*2.0} period: {human_readable(scenario[0])}, variables: {scenario[1]}"

        response = self.client.get(name=name, url="/collections/observations/area", params=params, headers=self.headers)
        # if response.status_code == 200:
        #     print(sz*2.0, len(response.json().get("coverages", [])))
        if response.status_code != 200:
            logger.info(params)
            logger.info(
                f"Response status code: {response.status_code}; Scenario {name} Response body: {response.text};"
            )

    # @task
    # def get_data_single_station_single_parameter_last_x_hours(self):
    #     hours = random.choice(hours_choice)
    #     date_time = datetime.now(UTC) - timedelta(hours=hours)
    #     dt_string = date_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    #     station_id = random.choice(self.station_ids)
    #     n_parameters = random.choice(n_parameters_choice)
    #     parameters = ",".join(random.sample(self.stations[station_id], n_parameters))
    #     # parameters = random.choice(self.stations[station_id])
    #     self.client.get(
    #         f"/collections/observations/locations/{station_id}?parameter-name={parameters}&datetime={dt_string}/..",
    #         name=f"location, {hours:02d} hours, {n_parameters} parameters",
    #         headers=headers,
    #     )

    # @task
    # def get_data_single_position_single_parameter(self):
    #     (lon, lat) = random.choice(self.station_locations)
    #     parameter = random.choice(self.stations_by_location[(lon, lat)])
    #     self.client.get(
    #         f"/collections/observations/position?coords=POINT({lon} {lat})&parameter-name={parameter}",
    #         name="position",
    #         headers=headers,
    #     )
    #
    # @task
    # def get_data_area_single_parameter_last_hour(self):
    #     date_time = datetime.now(UTC) - timedelta(hours=1)
    #     dt_string = date_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    #     standard_name = random.choice(common_standard_names)
    #     (cx, cy) = random.choice(self.station_locations)
    #     sz = random.choice(polygon_size) / 2.0
    #     left = cx - sz
    #     bottom = cy - sz
    #     right = cx + sz
    #     top = cy + sz
    #     polygon = f"POLYGON(({left} {bottom},{right} {bottom},{right} {top},{left} {top},{left} {bottom}))"
    #     url =
    #     f"/collections/observations/area?coords={polygon}&standard_names={standard_name}&datetime={dt_string}/.."
    #     self.client.get(url, name=f"area {sz * 2.0}deg x {sz * 2.0}deg x 1h", headers=headers)
    #     # if sz == 2.0:
    #     #     j = response.json()
    #     #     # print(sz*2.0)
    #     #     if response.status_code != 200:
    #     #         print(0)
    #     #     elif j["type"] == "CoverageCollection":
    #     #         print(len(j["coverages"]))
    #     #     else:
    #     #         print(1)
    #     # # print(j)
