import os
from functools import cache

import datastore_pb2_grpc as dstore_grpc
import grpc

# Functions in this file should be async,
# These functions should be the only components that are
# dependent on external services.


# Reuse channel and stub as much as possible, see https://grpc.io/docs/guides/performance/
@cache
def get_grpc_stub():
    channel = grpc.aio.insecure_channel(
        f"{os.getenv('DSHOST', 'localhost')}:{os.getenv('DSPORT', '50050')}",
        options=[
            (
                "grpc.max_receive_message_length",
                int(os.getenv("GRPC_MAX_MESSAGE_SIZE", 4194304)),
            )
        ],
    )
    return dstore_grpc.DatastoreStub(channel)


async def get_obs_request(request):
    grpc_stub = get_grpc_stub()
    response = await grpc_stub.GetObservations(request)

    return response


async def get_ts_ag_request(request):
    grpc_stub = get_grpc_stub()
    response = await grpc_stub.GetTSAttrGroups(request)
    return response


async def get_extents_request(request):
    grpc_stub = get_grpc_stub()
    response = await grpc_stub.GetExtents(request)
    return response


async def get_locations_request(request):
    grpc_stub = get_grpc_stub()
    response = await grpc_stub.GetLocations(request)
    return response
