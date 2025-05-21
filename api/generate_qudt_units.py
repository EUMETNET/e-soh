from rdflib import Graph, Namespace
import json


def generate_qudt_dictionary():
    """
    Function for generating a dictionary of QUDT units.
    """
    QUDT = Namespace("http://qudt.org/schema/qudt/")
    SKOS = Namespace("http://www.w3.org/2004/02/skos/core")

    g = Graph()
    g.parse("http://qudt.org/3.1.1/vocab/unit", format="turtle")

    qudt_dict = {}
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
                qudt_dict[str(ucum)] = unit_info
        else:
            unit_key = str(unit_uri).split("/")[-1].lower()
            qudt_dict[unit_key] = unit_info
        # if there is an alternative label, add it to the dictionary
        if alt:
            qudt_dict[str(alt)] = unit_info
    return qudt_dict


def main():
    qudt_dict = generate_qudt_dictionary()
    with open("constants/qudt_units.json", "w", encoding="utf-8") as file:
        json.dump(qudt_dict, file)


if __name__ == "__main__":
    main()
