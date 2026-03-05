import json

from . import covjson

from bufr_tools import covjson2bufr


def convert_to_bufr(raw_data):
    cov_json = covjson.convert_to_covjson(raw_data)
    bufr_content = covjson2bufr(json.dumps(cov_json.model_dump(mode="json")))

    return bufr_content
