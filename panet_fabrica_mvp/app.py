from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st
from rdflib import Graph, RDF, RDFS, OWL, URIRef

API = 'https://api.test.datacite.org/dois'
PANET_BASE = 'http://purl.org/pan-science/PaNET/'
ONTOLOGY_URL = 'https://raw.githubusercontent.com/pan-ontologies/PaNET/master/releases/latest/PaNET.owl'
PANET_ROOT = 'http://purl.org/pan-science/PaNET/PaNET00001'

st.set_page_config(page_title='Fabrica PaNET semantic search', layout='wide')
st.title('Fabrica Test: PaNET semantic dataset search')
st.caption(f'DataCite Test repository')


def panet_subject(s):
    return any('panet' in str(s.get(k) or '').lower() for k in ('subjectScheme', 'schemeUri', 'valueUri'))


def canonical_uri(uri):
    if not uri:
        return ''
    value = str(uri).strip()
    if value.startswith('https://purl.org/pan-science/PaNET/'):
        return 'http://' + value[len('https://'):]
    return value


def title_of(a):
    titles = a.get('titles') or []
    return next((x.get('title') for x in titles if x.get('title')), '(Untitled)')


def fetch_records(username, password, max_records, only_datasets):
    auth = (username, password) if username and password else None
    params = {'client-id': username, 'page[size]': 100, 'page[cursor]': '1'}
    if only_datasets:
        params['resource-type-id'] = 'Dataset'
    url = API
    rows = []
    session = requests.Session()
    session.headers.update({'Accept': 'application/vnd.api+json', 'User-Agent': 'FabricaPaNETMVP/1.0 (research prototype)'})
    while url and len(rows) < max_records:
        response = session.get(url, params=params, auth=auth, timeout=35)
        response.raise_for_status()
        payload = response.json()
        batch = payload.get('data', [])
        rows.extend(batch[:max_records - len(rows)])
        next_url = (payload.get('links') or {}).get('next')
        # Follow only DataCite test API pagination links, never arbitrary hosts.
        if next_url:
            parsed = urlparse(next_url)
            if parsed.scheme != 'https' or parsed.netloc != 'api.test.datacite.org' or not parsed.path.startswith('/dois'):
                raise ValueError('Unexpected pagination URL from API')
        url, params = next_url, None
        if not batch:
            break
    return rows, bool(url)


@st.cache_resource(show_spinner='Loading PaNET ontology...')
def load_ontology(path, file_signature):
    g = Graph()
    g.parse(path)
    classes = {str(x) for x in g.subjects(RDF.type, OWL.Class) if isinstance(x, URIRef)}
    classes.update(str(x) for x in g.subjects(RDFS.subClassOf, None) if isinstance(x, URIRef))
    classes.update(str(x) for x in g.objects(None, RDFS.subClassOf) if isinstance(x, URIRef))
    labels = {}
    for uri in classes:
        names = [str(v) for v in g.objects(URIRef(uri), RDFS.label)]
        labels[uri] = names[0] if names else uri.rsplit('/', 1)[-1]
    return g, classes, labels


def descendants(graph, parent):
    root = URIRef(parent)
    return {canonical_uri(x) for x in graph.transitive_subjects(RDFS.subClassOf, root) if isinstance(x, URIRef)} | {canonical_uri(parent)}


with st.sidebar:
    st.header('Connection')

    username = st.text_input(
        'DataCite Test Repository ID',
        value=''
    )

    password = st.text_input(
        'DataCite Test repository password',
        type='password'
    )

    max_records = st.number_input('Maximum records to fetch', min_value=100, max_value=100000, value=5000, step=100)
    only_datasets = st.checkbox('Only resource type Dataset', value=True)
    st.header('Ontology')
    st.markdown('[PaNET official releases](https://github.com/pan-ontologies/PaNET/releases)')

ontology_path = Path(__file__).with_name('PaNET.owl')

ontology_path = Path(__file__).with_name('PaNET.owl')

if ontology_path.exists():
    try:
        graph, classes, labels = load_ontology(
            str(ontology_path),
            (ontology_path.stat().st_size, ontology_path.stat().st_mtime_ns)
        )
        st.success(f'Ontology loaded: {len(classes):,} technique classes')
    except Exception as exc:
        st.error(f'Could not parse ontology: {exc}')
        st.stop()
else:
    st.error('PaNET.owl not found. Please include it in the deployed repository.')
    st.stop()



if st.button('Fetch / refresh repository records', type='primary'):
    try:
        with st.spinner('Retrieving draft records from DataCite Test...'):
            records, truncated = fetch_records(
                username,
                password,
                int(max_records),
                only_datasets
            )

        st.session_state['records'] = records
        st.session_state['truncated'] = truncated

        st.success(f'Successfully retrieved {len(records)} records.')

    except requests.HTTPError as exc:
        st.error(f'DataCite API request failed: {exc}')

    except (requests.RequestException, ValueError) as exc:
        st.error(f'Could not fetch records: {exc}')


records = st.session_state.get('records')
if records is None:
    st.info('Click “Fetch / refresh repository records” to begin.')
    st.stop()

if st.session_state.get('truncated'):
    st.warning('Record limit reached: results may be incomplete. Increase Maximum records to fetch.')

panet_records = []
for record in records:
    attrs = record.get('attributes') or {}
    if only_datasets and (attrs.get('types') or {}).get('resourceTypeGeneral') != 'Dataset':
        continue
    subjects = [s for s in (attrs.get('subjects') or []) if panet_subject(s)]
    if subjects:
        panet_records.append({'doi': attrs.get('doi') or record.get('id'), 'title': title_of(attrs), 'subjects': subjects})

c1, c2, c3 = st.columns(3)
c1.metric('Retrieved DOI records', len(records))
c2.metric('Records with PaNET subjects', len(panet_records))
c3.metric('Distinct PaNET subject URIs', len({canonical_uri(s.get('valueUri')) for r in panet_records for s in r['subjects'] if s.get('valueUri')}))

with st.expander('Inspect PaNET annotations in repository'):
    annotation_rows = [{'DOI': r['doi'], 'Title': r['title'], 'Subject': s.get('subject', ''), 'Subject scheme': s.get('subjectScheme', ''), 'Value URI': s.get('valueUri', '')} for r in panet_records for s in r['subjects']]
    st.dataframe(pd.DataFrame(annotation_rows), use_container_width=True)
    if annotation_rows:
        st.download_button('Download annotations CSV', pd.DataFrame(annotation_rows).to_csv(index=False), 'panet_annotations.csv', 'text/csv')

if not graph:
    st.stop()

st.subheader('Semantic technique search')

# Get all subclasses of PaNET00001, including indirect subclasses
allowed_classes = descendants(graph, PANET_ROOT)

# Restrict dropdown to these classes
options = sorted(
    allowed_classes.intersection(
        {canonical_uri(uri) for uri in classes}
    ),
    key=lambda uri: (labels.get(uri, '').lower(), uri)
)

if not options:
    st.error(
        'No subclasses of PaNET00001 found. '
        'Check that the ontology contains this class.'
    )
    st.stop()
    
selected = st.selectbox('Select a PaNET technique', options, format_func=lambda x: f'{labels.get(x, x)} ({x.rsplit("/", 1)[-1]})')
include_subclasses = st.checkbox('Include all subclasses (transitive)', value=True)

if selected:
    expanded = descendants(graph, selected) if include_subclasses else {canonical_uri(selected)}
    with st.expander(f'Search expansion: {len(expanded)} ontology terms'):
        st.dataframe(pd.DataFrame([{'Technique': labels.get(u, u.rsplit('/', 1)[-1]), 'URI': u} for u in sorted(expanded)]), use_container_width=True)
    matches = []
    missing_uri_count = 0
    for r in panet_records:
        hits = []
        for s in r['subjects']:
            uri = canonical_uri(s.get('valueUri'))
            if not uri:
                missing_uri_count += 1
            if uri and uri in expanded:
                hits.append(s)
        if hits:
            matches.append({'Title': r['title'], 'DOI': r['doi'], 'DOI link': f'https://doi.test.datacite.org/{r["doi"]}', 'Matching technique(s)': '; '.join(str(s.get('subject') or labels.get(canonical_uri(s.get('valueUri')), '')) for s in hits), 'Match type': 'Exact' if any(canonical_uri(s.get('valueUri')) == canonical_uri(selected) for s in hits) else 'Subclass', 'Matching URI(s)': '; '.join(str(s.get('valueUri')) for s in hits)})
    st.write(f'**{len(matches)} matching datasets**')
    if missing_uri_count:
        st.caption(f'{missing_uri_count} PaNET subject annotations have no valueUri and cannot be matched reliably by ontology URI.')
    if matches:
        result_df = pd.DataFrame(matches)
        st.dataframe(result_df, use_container_width=True, column_config={'DOI link': st.column_config.LinkColumn('DOI link')})
        st.download_button('Download matching datasets CSV', result_df.to_csv(index=False), 'panet_search_results.csv', 'text/csv')
    else:
        st.info('No datasets match this technique. Check that the dataset subjects have PaNET valueUri identifiers and that the ontology version contains those terms.')

st.caption('Inference scope: explicit rdfs:subClassOf hierarchy (including transitive ancestors). Other OWL logical inferences require a reasoned ontology.')
