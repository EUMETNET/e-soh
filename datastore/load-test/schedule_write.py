import math
import os
import random
import time
import uuid
from collections import namedtuple
from datetime import datetime
from datetime import UTC

import grpc
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from google.protobuf.timestamp_pb2 import Timestamp
from variables import variable_info

import datastore_pb2 as dstore
import datastore_pb2_grpc as dstore_grpc

# from apscheduler.executors.pool import ProcessPoolExecutor


# TODO: We use one channel & client per process (not per thread!). Check if this limits performance!
# Want to try with one channel per metoffice (so split over 20 channels)
# See also the fourth bullet here: https://grpc.io/docs/guides/performance/
channel = grpc.insecure_channel(f"{os.getenv('DSHOST', 'localhost')}:{os.getenv('DSPORT', '50050')}")
client = dstore_grpc.DatastoreStub(channel=channel)


crons = [
    (1, "*"),  # every minutes
    (5, "*/5"),  # every 5 minutes, on the five
    (5, "1-59/5"),  # every 5 minutes, on minute after the five
    (5, "2-59/5"),
    (5, "3-59/5"),
    (5, "4-59/5"),
    (10, "*/10"),  # every 10 minutes, on the 10
    (10, "1-59/10"),  # every 10 minutes, on minute after the five
    (10, "2-59/10"),
    (10, "3-59/10"),
    (10, "4-59/10"),
    (10, "5-59/10"),
    (10, "6-59/10"),
    (10, "7-59/10"),
    (10, "8-59/10"),
    (10, "9-59/10"),
]

vars_per_station = 40  # Should be <=44

Station = namedtuple("Station", "id lat lon period")


def write_data(station):
    pub_time = datetime.now(UTC)
    # Round observation time to nearest 1, 5, 10 minutes
    obs_time = pub_time.replace(minute=int(pub_time.minute / station.period) * station.period, second=0, microsecond=0)
    pub_ts = Timestamp()
    obs_ts = Timestamp()
    pub_ts.FromDatetime(pub_time)
    obs_ts.FromDatetime(obs_time)
    observations = []
    for var in range(0, vars_per_station):
        param_id, long_name, standard_name, unit = variable_info[var]
        ts_mdata = dstore.TSMetadata(
            platform=station.id,
            instrument=param_id,
            title=long_name,
            standard_name=standard_name,
            unit=unit,
            parameter_name=f"{standard_name}_2.0m_{param_id}_PT10M",  # HACK: Putting {param_id} here is a hack
        )
        obs_mdata = dstore.ObsMetadata(
            id=str(uuid.uuid4()),
            pubtime=pub_ts,
            geo_point=dstore.Point(lat=station.lat, lon=station.lon),  # One random per station
            obstime_instant=obs_ts,
            value=str(math.sin(time.mktime(obs_time.timetuple()) / 36000.0) + 2 * var),  # TODO: Make dependent station
        )
        observations.append(dstore.Metadata1(ts_mdata=ts_mdata, obs_mdata=obs_mdata))

    request_messages = dstore.PutObsRequest(observations=observations)
    response = client.PutObservations(request_messages)
    assert response.status == -1


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    # scheduler.add_executor(ProcessPoolExecutor())
    scheduler.add_executor(ThreadPoolExecutor())
    print(f"Now: {datetime.now()}", flush=True)
    for i in range(0, 5000):
        period, cron = random.choice(crons)
        station_id = f"station{i:04d}"
        station = Station(station_id, random.uniform(50.0, 55.0), random.uniform(4.0, 8.0), period)
        # print(station_id, cron, period)
        # TODO: Spread less well over time, for example, all use same second, but add jitter < 60
        trigger = CronTrigger(minute=cron, second=random.randint(0, 59), jitter=1)
        scheduler.add_job(write_data, args=(station,), id=station_id, name=station_id, trigger=trigger)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down...", flush=True)
