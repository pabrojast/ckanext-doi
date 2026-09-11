"""Regression coverage for citations of records with externally supplied DOIs."""

import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader

from ckanext.doi.lib.citation_export import export_citation, get_publisher
from ckanext.doi.lib.helpers import (
    get_citation_publisher,
    package_get_year,
    parse_json_authors,
)
from ckan.plugins import toolkit


@pytest.fixture
def record():
    return {
        'id': 'citation-regression',
        'name': 'citation-regression',
        'type': 'dataset',
        'title': 'Water study',
        'metadata_created': '2026-09-10T00:00:00',
        'publication_year': '2020',
        'authors': [{'name': 'Author supplied'}],
        'custom_doi': 'https://doi.org/10.1234/external',
        'doi': '10.1234/internal',
        'doi_status': True,
        'doi_date_published': '2026-09-10',
        'doi_publisher': 'IHP-WINS',
        'publisher_name': 'Publisher supplied',
    }


@pytest.fixture
def render():
    templates = Path(__file__).resolve().parents[1] / 'ckanext/doi/theme/templates'
    env = Environment(loader=FileSystemLoader(templates), autoescape=True,
                      extensions=['jinja2.ext.loopcontrols'])
    helpers = SimpleNamespace(
        doi_get_citation_publisher=get_citation_publisher,
        parse_json_authors=parse_json_authors,
        package_get_year=package_get_year,
        url_for=lambda *args, **kwargs: 'https://example.org/resource/test',
        now=datetime.now,
        render_datetime=lambda *args, **kwargs: '2026-09-10',
    )

    def render_citation(record, resource=False):
        name = 'resource_citation.html' if resource else 'package_citation.html'
        return env.get_template('doi/snippets/' + name).render(
            pkg_dict=record, res={'id': 'resource-test', 'name': 'Water data'},
            h=helpers, _=lambda text: text,
        )

    return render_citation


@pytest.mark.parametrize('doi_field', ['custom_doi', 'document_doi'])
@pytest.mark.parametrize('publisher', ['Publisher supplied', '', '  ', None, 'IHP-WINS'])
def test_external_publisher_never_uses_portal_default(record, doi_field, publisher):
    record[doi_field] = record.pop('custom_doi')
    record['publisher_name'] = publisher
    expected = (publisher or '').strip()
    assert get_citation_publisher(record, default='Portal default') == expected
    assert record['doi_publisher'] == 'IHP-WINS'


def test_publisher_field_fallback(record):
    record.update(publisher_name=' ', publisher='Legacy publisher')
    assert get_citation_publisher(record) == 'Legacy publisher'
    record['publisher_name'] = 'Preferred publisher'
    assert get_citation_publisher(record) == 'Preferred publisher'


def test_native_doi_retains_original_publisher_precedence(record, monkeypatch):
    record['custom_doi'] = ' '
    assert get_citation_publisher(record) == 'IHP-WINS'
    del record['doi_publisher']
    assert get_citation_publisher(record) == 'Publisher supplied'
    del record['publisher_name']
    monkeypatch.setitem(toolkit.config, 'ckanext.doi.publisher', 'Portal default')
    assert get_publisher(record) == 'Portal default'


@pytest.mark.parametrize('kind', ['dataset', 'documents'])
@pytest.mark.parametrize('legacy', [False, True])
@pytest.mark.parametrize('resource', [False, True])
@pytest.mark.parametrize('publisher', ['Publisher supplied', ''])
def test_rendered_citations_keep_record_metadata(record, render, kind, legacy, resource, publisher):
    record['type'] = kind
    authors = record.pop('authors')
    if legacy:
        record['author'] = 'Author supplied'
    else:
        record['authors_json' if kind == 'documents' else 'authors'] = authors
    record['publisher_name'] = publisher
    rendered = render(record, resource=resource)
    assert 'Author supplied' in rendered
    assert 'IHP-WINS' not in rendered
    assert ('Publisher supplied' in rendered) == bool(publisher)
    assert 'None' not in rendered
    if not resource:
        assert '(2020)' in rendered
        assert ('[Document]' if kind == 'documents' else '[Data set]') in rendered
        assert record['custom_doi'] in rendered


@pytest.mark.parametrize('field', ['custom_citation', 'citation'])
def test_explicit_citation_is_not_rewritten(record, render, field):
    record[field] = 'Author supplied. Intentionally credited IHP-WINS.'
    rendered = render(record)
    citation = re.search(r'id="citation-string"[^>]*>(.*?)</div>', rendered, re.S)[1]
    assert citation.strip() == record[field]


def test_custom_citation_wins_over_automatic_citation(record, render):
    record.update(custom_citation='Manual citation', citation='Automatic citation')
    rendered = render(record)
    assert 'Manual citation' in rendered
    assert 'Automatic citation' not in rendered


@pytest.mark.parametrize('format_type, publisher_field', [
    ('bibtex', 'publisher ='), ('ris', 'PB  -'), ('endnote', '%I '), ('apa', None),
])
@pytest.mark.parametrize('doi_field', ['custom_doi', 'document_doi'])
@pytest.mark.parametrize('kind', ['dataset', 'documents'])
@pytest.mark.parametrize('publisher', ['Publisher supplied', ''])
def test_exports_use_record_publisher(record, format_type, publisher_field, doi_field, kind, publisher, monkeypatch):
    record[doi_field] = record.pop('custom_doi')
    if doi_field == 'document_doi':
        record[doi_field] = '10.1234/external'
    record['type'] = kind
    if kind == 'documents':
        record['authors_json'] = record.pop('authors')
    record['publisher_name'] = publisher
    monkeypatch.setitem(toolkit.config, 'ckanext.doi.publisher', 'Portal default')
    citation = export_citation(record, format_type)
    assert 'Author supplied' in citation
    assert 'IHP-WINS' not in citation
    assert 'Portal default' not in citation
    assert '10.1234/external' in citation
    assert ('Publisher supplied' in citation) == bool(publisher)
    if publisher_field:
        assert (publisher_field in citation) == bool(publisher)
    else:
        assert '. .' not in citation


@pytest.mark.parametrize('format_type', ['bibtex', 'ris', 'endnote', 'apa'])
def test_native_exports_still_use_doi_publisher(record, format_type):
    del record['custom_doi']
    assert 'IHP-WINS' in export_citation(record, format_type)
