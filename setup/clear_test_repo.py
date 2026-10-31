import os
import json
import requests
import time

API_URL = "https://api.test.datacite.org/dois"

## Uncomment to enter credentials manually instead of using environment variables
# REPO_ID = getpass("DataCite Fabrica Test repository ID: ")
# PASSWORD = getpass("DataCite Fabrica Test password: ")

## Use environment variables to enter credentials
USERNAME = os.environ["DATACITE_REPO_ID"]
PASSWORD = os.environ["DATACITE_PASSWORD"]

INPUT_FILE = "{insert path here}/populate_repo_results.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    records = json.load(f)

session = requests.Session()
session.auth = (USERNAME, PASSWORD)

for record in records:

    if record.get("status") != "success":
        continue

    doi = record.get("test_doi")
    
    if not doi:
        continue

    url = f"{API_URL}/{doi}"

    # Check the DOI state before deleting
    response = session.get(url, timeout=30)
    response.raise_for_status()

    state = response.json()["data"]["attributes"]["state"]

    if state != "draft":
        print(f"Skipping {doi}: state is {state}")
        continue

    response = session.delete(url, timeout=30)

    if response.status_code == 204:
        print(f"Deleted: {doi}")
    else:
        print(f"Failed: {doi} ({response.status_code})")
        print(response.text)

    time.sleep(0.3)