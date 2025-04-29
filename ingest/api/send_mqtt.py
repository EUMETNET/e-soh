import os
import logging
import json
from paho.mqtt import client as mqtt_client
from fastapi import HTTPException

logger = logging.getLogger(__name__)

if "MQTT_TOPIC_PREPEND" in os.environ:
    mqtt_topic_prepend = os.getenv("MQTT_TOPIC_PREPEND", "")
    mqtt_topic_prepend = mqtt_topic_prepend if mqtt_topic_prepend.endswith("/") else mqtt_topic_prepend + "/"


def connect_mqtt(mqtt_conf: dict):
    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
        else:
            logger.error(f"Failed to connect, return code  {rc}")

    def on_disconnect(client, userdata, flags, rc, properties):
        logger.warning(f"Disconnected from MQTT broker with result code {str(rc)}")

    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
    client.enable_logger(logger)
    client.username_pw_set(mqtt_conf["username"], mqtt_conf["password"])

    if mqtt_conf["enable_tls"]:
        client.tls_set()

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    client.connect(mqtt_conf["host"], mqtt_conf["port"])
    client.loop_start()
    return client


def send_message(topic: str, message: str, client: object):
    if len(topic) != 0:
        mqtt_topic = mqtt_topic_prepend + topic
    try:
        if isinstance(message, dict):
            client.publish(mqtt_topic, json.dumps(message))
        elif isinstance(message, (str, bytes)):
            client.publish(mqtt_topic, message)
        else:
            raise TypeError("Mqtt message of unknown type")

    except Exception as e:
        logger.critical(str(e), message, type(message))
        raise HTTPException(status_code=500, detail="Failed to publish to mqtt")
