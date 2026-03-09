import json

from . import covjson

from bufr_tools import covjson2bufr


def convert_to_bufr(raw_data: str):
    cov_json = covjson.convert_to_covjson(raw_data)
    print(cov_json)
    bufr_content = covjson2bufr.covjson2bufr(json.dumps(cov_json))
    print(bufr_content)

    if not bufr_content and not cov_json:
        raise ValueError("No content")
    return bufr_content
