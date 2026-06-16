import logging
import os
import json
from collections import deque

from functools import cache

import datastore_pb2 as dstore
import datastore_pb2_grpc as dstore_grpc

import grpc
from fastapi import HTTPException

logger = logging.getLogger(__name__)


@cache
def get_grpc_stub():
    options = []
    grpc_config = json.dumps(
        {
            "methodConfig": [
                {
                    "name": [{}],
                    "retryPolicy": {
                        "maxAttempts": 5,
                        "initialBackoff": "0.5s",
                        "maxBackoff": "8s",
                        "backoffMultiplier": 2,
                        "retryableStatusCodes": ["INTERNAL", "UNAVAILABLE", "OUT_OF_RANGE"],
                    },
                }
            ]
        }
    )
    options.append(("grpc.enable_retries", 1))
    options.append(("grpc.service_config", grpc_config))
    channel = grpc.aio.insecure_channel(
        f"{os.getenv('DSHOST', 'store')}:{os.getenv('DSPORT', '50050')}", options=options
    )

    return dstore_grpc.DatastoreStub(channel)


async def putObsRequest(put_obs_request):
    # create overall set of observations to be inserted in the store
    grpc_stub = get_grpc_stub()

    stack = deque()
    obs = put_obs_request.observations

    if len(obs) > 0:
        stack.append(obs)  # push overall set on stack

    tot_inserted = 0  # total observations succesfully inserted
    tot_calls = 0  # total calls to PutObservations

    while len(stack) > 0:  # while more (sub)sets remain
        # try to insert next (sub)set in the store
        obs0 = stack.pop()
        request = dstore.PutObsRequest(observations=obs0)

        try:
            await grpc_stub.PutObservations(request)
            tot_inserted += len(obs0)
            tot_calls += 1
        except grpc.RpcError as grpc_error:
            if grpc_error.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
                if len(obs0) == 1:  # give up, since even a single observation
                    # (that may not be split further!) is too big for a single message
                    print("error: even a single obs is too big for a single message")
                    break

                # split obs0 into two subsets, push both on stack,
                # and try again
                m = len(obs0) // 2
                obs1, obs2 = obs0[:m], obs0[m:]
                if len(obs1) > 0:
                    stack.append(obs1)
                if len(obs2) > 0:
                    stack.append(obs2)
                continue

            # give up
            logger.critical(f"RPC call failed: {grpc_error.code()}\n{grpc_error.details()}")
            raise HTTPException(detail=f"GRPC_ERROR:{grpc_error.details()}", status_code=400)

    # NOTE: at this point, the overall set of observations has been completely
    # inserted in the store only if no errors occurred in the above loop
    logger.debug("RPC call succeeded. len {0} total insert {1} total calls {2}"
                 .format(len(obs), tot_inserted, tot_calls))
    # return len(obs), tot_inserted, tot_calls
