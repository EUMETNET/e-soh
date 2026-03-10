import os
import warnings


WIS2_TOPIC = os.getenv("WIS2_TOPIC")
WIS2_DATA_ID = os.getenv("WIS2_DATA_ID")

WIS2_METADATA_RECORD_ID = os.getenv("WIS2_METADATA_RECORD_ID")
if not WIS2_METADATA_RECORD_ID:
    warnings.warn(
        "WIS2_METADATA_RECORD_ID env variable not set."
        " This is required for generating the WIS2 compliant payload. Please set it to a valid value."
    )
