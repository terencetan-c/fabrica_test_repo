import requests
import time
import json
# from getpass import getpass
import copy
import os


# ==========================================
# CONFIGURATION
# ==========================================

PREFIX = "10.85126"

## Uncomment to enter credentials manually instead of using environment variables
# REPO_ID = getpass("DataCite Fabrica Test repository ID: ")
# PASSWORD = getpass("DataCite Fabrica Test password: ")

## Use environment variables to enter credentials
REPO_ID = os.environ["DATACITE_REPO_ID"]
PASSWORD = os.environ["DATACITE_PASSWORD"]

TEST_API = "https://api.test.datacite.org/dois"

INPUT_FILE = "{insert path here}/selected_dois_full.json"
OUTPUT_FILE = "{insert path here}/populate_repo_results.json"

DELAY = 0.3



# Supported descriptive metadata fields
METADATA_FIELDS = {
    "creators",
    "titles",
    "publisher",
    "publicationYear",
    "types",
    "subjects",
    "contributors",
    "dates",
    "language",
    "alternateIdentifiers",
    "relatedIdentifiers",
    "sizes",
    "formats",
    "version",
    "rightsList",
    "descriptions",
    "geoLocations",
    "fundingReferences",
    "relatedItems",
    "url",
}


# ==========================================
# PREPARE RECORD
# ==========================================

def prepare_record(dataset):
    original = dataset["attributes"]

     # Preserve all supported descriptive metadata
    attributes = {
        key: copy.deepcopy(value)
        for key, value in original.items()
        if key in METADATA_FIELDS and value is not None
    }

    # Assign test repository prefix
    attributes["prefix"] = PREFIX

    # Do not copy the original DOI or suffix.
    # DataCite generates a new DOI.

    # No event="publish": request a draft DOI
    return {
        "data": {
            "type": "dois",
            "attributes": attributes
        }
    }


# ==========================================
# LOAD ORIGINAL RECORDS
# ==========================================

def load_records():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            return data["data"]

        if "attributes" in data:
            return [data]

        if isinstance(data.get("data"), dict):
            return [data["data"]]

    raise ValueError("Unsupported DataCite JSON structure")



# ==========================================
# LOAD PREVIOUS RESULTS IF THEY EXIST
# ==========================================

def load_results():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return []


# ==========================================
# IMPORT RECORDS
# ==========================================


def import_records():
    records = load_records()
    results = load_results()

    # Find records already imported successfully
    imported = {
        result["original_doi"]
        for result in results
        if result.get("status") == "success"
    }

    print(f"Loaded {len(records)} records")
    print(f"Previously imported: {len(imported)}")

    session = requests.Session()
    session.auth = (REPO_ID, PASSWORD)
    session.headers.update({
        "Content-Type": "application/vnd.api+json",
        "Accept": "application/vnd.api+json",
    })

    attempted = 0

    for dataset in records:

        original_doi = dataset["id"]

        if original_doi in imported:
            print(f"Skipping existing: {original_doi}")
            continue

        attempted += 1
        print(f"\n[{attempted}/{len(records)}] {original_doi}")

        try:
            payload = prepare_record(dataset)

            response = session.post(
                TEST_API,
                json=payload,
                timeout=30
            )

            if response.status_code == 201:
                result = response.json()["data"]
                new_doi = result["id"]
                state = result["attributes"].get("state")

                print(f"Created: {new_doi}")
                print(f"State: {state}")

                record_result = {
                    "original_doi": original_doi,
                    "test_doi": new_doi,
                    "status": "success",
                    "http_status": response.status_code,
                    "state": state,
                    "error": None
                }

                imported.add(original_doi)

            else:
                print(f"Failed: {response.status_code}")
                print(response.text[:1000])

                record_result = {
                    "original_doi": original_doi,
                    "test_doi": None,
                    "status": "failed",
                    "http_status": response.status_code,
                    "state": None,
                    "error": response.text[:2000]
                }

        except requests.RequestException as e:
            print(f"Request error: {e}")

            record_result = {
                "original_doi": original_doi,
                "test_doi": None,
                "status": "failed",
                "http_status": None,
                "state": None,
                "error": str(e)
            }

        # Add result to existing results
        results.append(record_result)

        # Save updated results as JSON
        # Write to a temporary file first to avoid
        # leaving partially written JSON.
        temp_file = OUTPUT_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

        os.replace(temp_file, OUTPUT_FILE)

        time.sleep(DELAY)

    print("\nImport finished.")
    print(f"Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    import_records()