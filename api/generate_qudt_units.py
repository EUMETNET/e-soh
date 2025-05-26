from rdflib import Graph, Namespace
import json


def get_qudt_units():
    """
    Function for generating a dictionary of QUDT units for all units in the QUDT vocabulary.
    """
    QUDT = Namespace("http://qudt.org/schema/qudt/")
    SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

    g = Graph()
    g.parse("http://qudt.org/3.1.1/vocab/unit", format="turtle")

    qudt_units = {}
    for unit_uri in g.subjects(predicate=None, object=QUDT.Unit):
        ucum_codes = list(g.objects(subject=unit_uri, predicate=QUDT.ucumCode))
        symbol = next(g.objects(subject=unit_uri, predicate=QUDT.symbol), None)
        alt = next(g.objects(subject=unit_uri, predicate=SKOS.altLabel), None)

        unit_info = {
            "type": str(unit_uri).replace("http://", "https://"),
            "value": str(symbol) if symbol else str(unit_uri).split("/")[-1].lower(),
        }

        # In some cases there is no ucumCode so use the unit URI as the key
        if ucum_codes:
            for ucum in ucum_codes:
                qudt_units[str(ucum)] = unit_info
        else:
            unit_key = str(unit_uri).split("/")[-1].lower()
            qudt_units[unit_key] = unit_info
        # if there is an alternative label, add it to the dictionary
        if alt:
            qudt_units[str(alt)] = unit_info
    return qudt_units


def generate_qudt_dictionary(qudt_units, std_units_file):
    """
    Function for generating a dictionary for the used QUDT units in the system.
    Based on all QUDT units and std_name_units used with ingestion.
    """
    with open(std_units_file, "r", encoding="utf-8") as file:
        std_units_data = json.load(file)

    qudt_dict = {}
    for key, value in std_units_data.items():
        qudt_dict[key] = {
            "type": qudt_units.get(value["unit"], {}).get("type", "https://qudt.org/schema/qudt/UNKNOWN"),
            "value": qudt_units.get(value["unit"], {}).get("value", "-"),
        }
    return qudt_dict


def main():
    qudt_units = get_qudt_units()
    qudt_dict = generate_qudt_dictionary(qudt_units, "std_name_units.json")
    with open("constants/qudt_units.json", "w", encoding="utf-8") as file:
        json.dump(qudt_dict, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
