import glob
import pytest
from jsonschema import ValidationError
from api.model import JsonMessageSchema
from api.messages import build_all_json_payloads_from_bufr
from bufr_tools.bufresohmsg_py import init_bufrtables_py


@pytest.mark.timeout(1000)
@pytest.mark.parametrize("bufr_file_path", glob.glob("test/test_data/bufr/*.buf*"))
def test_verify_json_payload_bufr(bufr_file_path, capsys):

    init_bufrtables_py("")

    with open(bufr_file_path, "rb") as file:
        bufr_content = file.read()

    json_payloads = build_all_json_payloads_from_bufr(bufr_content)

    for payload in json_payloads:
        try:
            instant = JsonMessageSchema(**payload)

            assert instant is not None
            assert isinstance(instant, JsonMessageSchema)
        except ValidationError as e:
            print(e)
            raise ValidationError(e)
