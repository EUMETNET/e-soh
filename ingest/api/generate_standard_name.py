import xml.etree.ElementTree as ET

import requests


# Create element tree object
root = ET.fromstring(
    requests.get("https://cf-convention.github.io/Data/cf-standard-names/84/src/cf-standard-name-table.xml").content
)

# Find all 'entry' elements and get their 'id' attribute
with open("api/cf_standard_names_v84.txt", "w") as file:
    for entry in root.findall("entry"):
        file.write(f"{entry.get('id')}\n")


# Find all 'alias' elements and get their 'id' attribute
with open("api/cf_standard_names_alias_v84.txt", "w") as file:
    for alias in root.findall("alias"):
        file.write(f"{alias.find('entry_id').text}:{alias.get('id')}\n")
