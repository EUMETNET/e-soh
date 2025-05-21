import copy
import json

import numpy as np
import xarray as xr

from ingest.netCDF.mapper import Mapper


def get_attrs(ds: xr.Dataset, var: str):
    """
    Get the attributes from the correct level in netCDF
    """
    metdata_dict = getattr(ds, var)
    if hasattr(metdata_dict, "attrs"):
        return metdata_dict.attrs
    elif hasattr(metdata_dict, "attr"):
        return metdata_dict.attr
    else:
        return metdata_dict


def create_json_from_netcdf_metdata(ds: xr.Dataset, map_netcdf: dict) -> str:
    """
    This function takes a netCDF file with ACDD and CF standard
    and creates a json string containing specified metadata fields
    in the e-soh-message-spec json schema. This function only extract the
    constant fields from the netcdf.

    Keyword arguemnts:
    path (xr.Dataset) -- An instance of a xr.Dataset loaded from a netCDF
    map_netcdf (dict) -- a json formated for datafield parsing from netCDF

    Return:
    str -- a json in string format

    """

    def get_metadata_dict(ds: xr.Dataset, json_message_target: dict, sub_map: dict) -> None:
        """
        This function updates the json_message_target dict with fields from the netCDF.

        Keyword arguents:
        ds (xarray.Dataset) -- A netCDF loaded in to a xarray dataset.
        json_message_target (dict) -- This dict is where all extracted metadata is stored.
        sub_map (dict) -- This is a sub-dict from the entire json specifying
                          how to extract metadata fields
        """
        if "translation_fields" in sub_map:
            for netcdf_attr_target in sub_map["translation_fields"]:
                netcdf_metadata = get_attrs(ds, netcdf_attr_target)
                current_sub_dict = sub_map["translation_fields"][netcdf_attr_target]

                json_message_target.update(populate_json_message({}, netcdf_metadata, current_sub_dict))

        if "persistant_fields" in sub_map:
            for netcdf_attr_target in sub_map["persistant_fields"]:
                netcdf_metadata = get_attrs(ds, netcdf_attr_target)
                current_sub_dict = sub_map["persistant_fields"][netcdf_attr_target]

                json_message_target.update(
                    {i: netcdf_metadata[i] for i in sub_map["persistant_fields"][netcdf_attr_target]}
                )

    def populate_json_message(json_message_target: dict, netcdf_metadata: dict, current_sub_dict: dict) -> dict:
        """
        This function contains the loop for actually adding values in to the json_message_target.

        Keyword arguents:
        json_message_target (dict) -- This dict is where all extracted metadata is stored.
        netcdf_metadata (dict) -- This dict contains a dict of all metadata fields from a variable,
                                  or the global variables.
        sub_map (dict) -- This is a sub-dict from the entire json specifying how to
                          extract metadata fields
        """

        for key in current_sub_dict:
            if key == "inpt_type":
                continue
            match current_sub_dict[key]["inpt_type"]:
                case "str":
                    json_message_target[key] = f"{current_sub_dict[key]['sep']}".join(
                        [netcdf_metadata[i] for i in current_sub_dict[key]["fields"]]
                    )

                case "list":
                    json_message_target[key] = [netcdf_metadata[field] for field in current_sub_dict[key]["fields"]]

                case "raw":
                    json_message_target[key] = current_sub_dict[key]["value"]

                case "multi":
                    if key not in json_message_target:
                        json_message_target[key] = {}

                    json_message_target[key].update(populate_json_message({}, netcdf_metadata, current_sub_dict[key]))

        return json_message_target

    def populate_links(ds: xr.Dataset, json_message_target: dict, sub_map: dict) -> None:
        """
        This function updates the json_message_target dict with fields from the netCDF.
        Perform same task as get_metadata_dict

        Keyword arguents:
        ds (xarray.Dataset) -- A netCDF loaded in to a xarray dataset.
        json_message_target (dict) -- This dict is where all extracted metadata is stored.
        sub_map (dict) -- This is a sub-dict from the entire json specifying
                          how to extract metadata fields
        """
        for netcdf_attr_target in sub_map["translation_fields"]:
            netcdf_metadata = get_attrs(ds, netcdf_attr_target)
            current_sub_dict = sub_map["translation_fields"][netcdf_attr_target]

            json_message_target += [populate_json_message({}, netcdf_metadata, i) for i in current_sub_dict]

            if "persistant_fields" in sub_map:
                pass

    message_json = {"properties": {}, "links": []}

    get_metadata_dict(ds, message_json, map_netcdf["root"])
    get_metadata_dict(ds, message_json["properties"], map_netcdf["properties"])
    populate_links(ds, message_json["links"], map_netcdf["links"])

    # Perform some transformations to comply with message schema
    message_json["geometry"]["type"] = (
        message_json["geometry"]["type"][0].upper() + message_json["geometry"]["type"][1:].lower()
    )
    coordinates = {"lat": message_json["geometry"]["coordinates"][0], "lon": message_json["geometry"]["coordinates"][1]}
    message_json["geometry"]["coordinates"] = coordinates

    return json.dumps(message_json)


def build_all_json_payloads_from_netcdf(
    ds: xr.Dataset, schema_path: str, timediff: np.timedelta64 = np.timedelta64(1, "D")
) -> list[str]:
    """
    This function expects a xarray.Dataset with observations from one station.
    Will only extract data from variable that have the "standard_name" metadata field set.

    ### Keyword arguments:
    ds (xarray.Dataset) -- A netCDF loaded in to a xarray dataset
    mapping_json (dict) -- The json that specifies how metadata should be mapped from
                           netCDF to mqtt message

    Returns:
    list[dict] -- returns a list with mqtt messages,
                  one for each variable for each timestep in the interval specified.

    ## The mapping json
    The mapping json contians all information about how \n
    and what fields to parse from the netCDF data.
    The E-SOH message spec has 2 sub-json fields and some top-level data fields.
    These are also the top level fields in the mapping json.
    On the top level the name "root" is resverd for defining variables \n
    that should be on the root level of the mqtt message json.
    "properties" and "links" are defined fields in the mqtt message spec. At the root level of the
    mapping json, any other fields are ignored.
    Each of the root-level fields in the mapping json can contain two subfields.
    "traslation_fields" and "persistant_fields", "translation_fields" contains the
    fields that can not be directly translated from the netCDF metadata.
    "persistant_fields" contains a list of all fields that can be directly lifted\n
    over to the mqtt message json.
    In both "persistant_fields" and "translation_fields" the can be an unlimited number of fields.
    Here, the name of each field should be the same name
    from which we should import metadata from in the netCDF.
    For getting global attributes the name "attrs" should be used.
    For each attribute to map, we create a block.
    Each allowed block is described below.

    ```
    "name_of_field_in_the_mqtt_message": {
        "fields": [ a list of metadata fields to get from current variable ]
        "inpt_type": "str" #This inpt_type will procure a string from all variables
                            listet in fields, separated by sep
        "sep": "the separator between each variable in fields
    }

    "name_of_field_in_the_mqtt_message": {
        "fields": [ a list of metadata fields to get from current variable ]
        "inpt_type": "list" # Will gather all metadata fields in to a list

    }

    "name_of_field_in_the_mqtt_message": {
        "value": "string to be put in to mqtt message"
        "inpt_type": "raw" # This inpt_type will take the data in the value field
                             and put it in the mqtt message

    }

    "name_of_field_in_the_mqtt_message": {
        { A dict containing more allowed blocks }
        "inpt_type": "multi" # This field indicates that there are more block in a dict here.
                               Will recursivly resolve "multi" inpt_types
                               meaning they can be nested
    }
    ```
    """

    mapping_json = Mapper(schema_path)(ds.attrs["institution"])

    json_msg = create_json_from_netcdf_metdata(ds, mapping_json)

    json_msg = json.loads(json_msg)

    json_msg["version"] = "v4.0"

    messages = []

    ds_subset = ds.sel(time=slice(ds.time[-1] - timediff, ds.time[-1]))

    for obs_set in ds_subset:
        if obs_set in mapping_json["ignore"]:
            continue
        data = ds_subset[obs_set]
        if "standard_name" not in data.attrs:
            continue
        for value, time in zip(data.data, data.time.data):
            time = np.datetime_as_string(time, unit="μs", timezone="UTC")
            json_msg["properties"]["datetime"] = time

            content_str = f"{value}"
            content = {
                "encoding": "utf-8",
                "standard_name": data.attrs["standard_name"],
                "unit": data.attrs["units"],
                "size": len(str.encode(content_str, "utf-8")),
                "value": content_str,
            }

            json_msg["properties"]["content"] = content

            messages.append(copy.deepcopy(json_msg))

    # Returns all complete messages
    return messages


if __name__ == "__main__":
    print("Load METno data")
    ds = xr.load_dataset("../../test/test_data/air_temperature_gullingen_skisenter-parent.nc")
    with open("../../schemas/netcdf_to_e_soh_message_metno.json") as file:
        j_read_netcdf = json.load(file)

    print(build_all_json_payloads_from_netcdf(ds, j_read_netcdf)[0], "\n\n\n\n")

    print("Load KNMI data")
    ds = xr.load_dataset("../../test/test_data/20221231.nc_bck")
    with open("../../schemas/netcdf_to_e_soh_message_knmi.json") as file:
        j_read_netcdf = json.load(file)

    for station in ds.station:
        print(build_all_json_payloads_from_netcdf(ds.sel(station=station), j_read_netcdf)[0])
