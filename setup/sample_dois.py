import requests
import json


# Randomly select 100 DataCite datasets
url = "https://api.datacite.org/dois"

response = requests.get(
    url,
    params={
        "resource-type-id": "dataset",
        "random": "true",
        "page[size]": 100,
        "disable-facets": "true"
    },
    timeout=30
)

response.raise_for_status()

datasets = response.json()["data"]


# Save the randomly selected datasets for record-keeping
with open('{insert path here}/selected_dois.json','w') as f:
    json.dump([dataset['id'] for dataset in datasets], f, indent=2)

with open('{insert path here}/selected_dois_full.json','w') as f:
    json.dump(datasets,f,indent=2)