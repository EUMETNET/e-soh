import logging
from typing import Union

from api.generate_wis2_payload import generate_wis2_payload
from api.generate_wis2_payload import generate_wis2_topic
import grpc
import json

from fastapi import HTTPException

from api.datastore import build_grpc_messages
from api.messages import build_messages
from api.send_mqtt import connect_mqtt, send_message
from api.grpc_putter import putObsRequest

import datastore_pb2 as dstore

from api.utilities import seconds_to_iso_8601_duration
from api.utilities import convert_to_meter

logger = logging.getLogger(__name__)


class IngestToPipeline:
    """
    This class should accept paths or objects to pass on to mqtt broker.
    """

    def __init__(
        self,
        mqtt_conf: dict,
        uuid_prefix: str,
        mqtt_WIS2_conf: dict | None = None,
    ):
        self.uuid_prefix = uuid_prefix
        self.client = None
        self.WIS2_client = None
        try:
            if mqtt_conf["host"]:
                self.client = connect_mqtt(mqtt_conf)
            if mqtt_WIS2_conf:
                self.WIS2_client = connect_mqtt(mqtt_WIS2_conf)
        except Exception as e:
            logger.error(
                "Failed to establish connection to mqtt, "
                + "\n"
                + str(e)
                + "\n"
                + json.dumps(mqtt_conf)
                + "\n"
                + json.dumps(mqtt_WIS2_conf)
            )
            raise e

    async def ingest(self, message: Union[str, object], publishWIS2: bool, baseURL: str):
        """
        This method will interpret call all methods for deciding input type, build the mqtt messages, and
        publish them.

        """
        messages = build_messages(message, self.uuid_prefix)
        await self.publish_messages(messages, publishWIS2, baseURL)

    async def publish_messages(self, messages: list, publishWIS2: bool, baseURL: str):
        """
        This method accepts a list of json strings ready to be ingest to datastore
         and published to the mqtt topic.
        """
        obs_requests = dstore.PutObsRequest(observations=[build_grpc_messages(msg) for msg in messages])
        try:
            await putObsRequest(obs_requests)
            logger.debug("Succesfully ingested to datastore")
        except grpc.RpcError as e:
            logger.error("Failed to reach datastore, " + "\n" + str(e))
            raise HTTPException(status_code=500, detail="API could not reach datastore")

        if self.client or self.WIS2_client:
            for msg in messages:
                topic = (
                    msg["properties"]["naming_authority"]
                    + "/"
                    + msg["properties"]["platform"]
                    + "/"
                    + msg["properties"]["content"]["standard_name"]
                )

                # modify the period back to iso format and level back to meter
                period_iso = seconds_to_iso_8601_duration(msg["properties"]["period"])
                level_string = convert_to_meter(msg["properties"]["level"])
                msg["properties"]["level"] = level_string
                msg["properties"]["period"] = period_iso
                try:
                    if self.client:
                        send_message(topic, json.dumps(msg), self.client)
                        logger.debug("Succesfully published to mqtt")
                except Exception as e:
                    logger.error("Failed to publish to mqtt, " + str(e))
                    raise HTTPException(
                        status_code=500,
                        detail="Data ingested to datastore. But unable to publish to mqtt",
                    )
                try:
                    if publishWIS2 and self.WIS2_client:
                        send_message(
                            generate_wis2_topic(),
                            generate_wis2_payload(msg, baseURL).model_dump(
                                exclude_unset=True, exclude_none=True, mode="json"
                            ),
                            self.WIS2_client,
                        )
                        logger.debug("Succesfully published to mqtt")
                except Exception as e:
                    logger.error("Failed to publish to WIS2 mqtt, " + str(e))
                    print(e)
                    raise HTTPException(
                        status_code=500,
                        detail="Data ingested to datastore. But unable to publish to WIS2 mqtt",
                    )
