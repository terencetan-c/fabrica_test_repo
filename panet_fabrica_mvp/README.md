# Fabrica Test + PaNET semantic search MVP

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Download an official PaNET OWL release from https://github.com/pan-ontologies/PaNET/releases and save it as `PaNET.owl` alongside `app.py`, **or** upload the OWL file in the app sidebar. Use an RDF/XML OWL file.

Click **Fetch / refresh repository records**. Unauthenticated requests retrieve Findable DOIs only. If your records are Draft or Registered, enter your DataCite **Test** repository credentials in the sidebar. These credentials are not stored on disk by this app.

Inspect PaNET subjects, then choose a parent technique. The app matches annotations using the `valueUri` field and transitive `rdfs:subClassOf` relationships. It displays exact vs subclass matches and provides CSV exports.

## Notes

- The app defaults to `resource-type-id=Dataset` and retrieves pages using DataCite's cursor pagination. Increase the record limit if needed.
- Only subjects whose `subjectScheme`, `schemeUri`, or `valueUri` contain `PaNET` (case-insensitive) are selected. Annotations missing `valueUri` cannot be matched reliably.
- The ontology version matters: ensure the chosen PaNET release includes the terms you deposited.
- This is subclass traversal, not complete OWL reasoning. Use a pre-reasoned ontology for inferred axioms.
- Stop Streamlit by pressing Ctrl+C in the terminal.
