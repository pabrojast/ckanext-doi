#!/usr/bin/env python3
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

from datetime import datetime
from ckan.plugins import toolkit
from ckanext.doi.lib.helpers import package_get_year, parse_json_authors


def get_authors_list(pkg_dict):
    """
    Extract authors from either enhanced authors field or legacy author field.
    Returns a list of author dictionaries with name, orcid, and affiliation.
    """
    authors = []
    
    # Check for enhanced authors field first
    enhanced_authors = pkg_dict.get('authors') or pkg_dict.get('authors_json')
    if enhanced_authors:
        for author in parse_json_authors(enhanced_authors):
            authors.append({
                'name': author.get('name', ''),
                'orcid': author.get('orcid', ''),
                'affiliation': author.get('affiliation', ''),
                'email': author.get('email', '')
            })
    
    # Fallback to legacy author field
    if not authors and pkg_dict.get('author'):
        authors.append({
            'name': pkg_dict.get('author'),
            'orcid': '',
            'affiliation': '',
            'email': pkg_dict.get('author_email', '')
        })
    
    return authors


def get_doi_url(pkg_dict):
    """Get the DOI URL, preferring custom DOI over generated DOI."""
    if pkg_dict.get('custom_doi'):
        return pkg_dict['custom_doi']
    elif pkg_dict.get('doi'):
        return f"https://doi.org/{pkg_dict['doi']}"
    return ""


def export_bibtex(pkg_dict):
    """Export citation in BibTeX format."""
    authors = get_authors_list(pkg_dict)
    doi_url = get_doi_url(pkg_dict)
    year = package_get_year(pkg_dict)
    
    # Create author string
    author_names = [author['name'] for author in authors if author['name']]
    author_str = ' and '.join(author_names) if author_names else 'Unknown'
    
    # Create BibTeX entry
    bibtex_id = pkg_dict.get('name', pkg_dict.get('id', 'dataset'))
    
    bibtex = f"""@dataset{{{bibtex_id},
    title = {{{pkg_dict.get('title', 'Untitled Dataset')}}},
    author = {{{author_str}}},
    year = {{{year}}},
    publisher = {{{pkg_dict.get('doi_publisher', toolkit.config.get('ckanext.doi.publisher', 'Unknown Publisher'))}}},"""
    
    if doi_url:
        bibtex += f"\n    doi = {{{doi_url.replace('https://doi.org/', '')}}},"
        bibtex += f"\n    url = {{{doi_url}}},"
    
    if pkg_dict.get('notes'):
        # Clean description for BibTeX
        description = pkg_dict['notes'].replace('\n', ' ').replace('\r', '')[:200]
        bibtex += f"\n    note = {{{description}...}},"
    
    bibtex += "\n}"
    
    return bibtex


def export_ris(pkg_dict):
    """Export citation in RIS format."""
    authors = get_authors_list(pkg_dict)
    doi_url = get_doi_url(pkg_dict)
    year = package_get_year(pkg_dict)
    
    ris = "TY  - DATA\n"
    ris += f"TI  - {pkg_dict.get('title', 'Untitled Dataset')}\n"
    
    # Add authors
    for author in authors:
        if author['name']:
            ris += f"AU  - {author['name']}\n"
    
    ris += f"PY  - {year}\n"
    ris += f"PB  - {pkg_dict.get('doi_publisher', toolkit.config.get('ckanext.doi.publisher', 'Unknown Publisher'))}\n"
    
    if doi_url:
        ris += f"DO  - {doi_url.replace('https://doi.org/', '')}\n"
        ris += f"UR  - {doi_url}\n"
    
    if pkg_dict.get('notes'):
        ris += f"AB  - {pkg_dict['notes']}\n"
    
    ris += "ER  - \n"
    
    return ris


def export_endnote(pkg_dict):
    """Export citation in EndNote format."""
    authors = get_authors_list(pkg_dict)
    doi_url = get_doi_url(pkg_dict)
    year = package_get_year(pkg_dict)
    
    endnote = "%0 Dataset\n"
    endnote += f"%T {pkg_dict.get('title', 'Untitled Dataset')}\n"
    
    # Add authors
    for author in authors:
        if author['name']:
            endnote += f"%A {author['name']}\n"
    
    endnote += f"%D {year}\n"
    endnote += f"%I {pkg_dict.get('doi_publisher', toolkit.config.get('ckanext.doi.publisher', 'Unknown Publisher'))}\n"
    
    if doi_url:
        endnote += f"%R {doi_url.replace('https://doi.org/', '')}\n"
        endnote += f"%U {doi_url}\n"
    
    if pkg_dict.get('notes'):
        endnote += f"%X {pkg_dict['notes']}\n"
    
    return endnote


def export_apa(pkg_dict):
    """Export citation in APA format."""
    authors = get_authors_list(pkg_dict)
    doi_url = get_doi_url(pkg_dict)
    year = package_get_year(pkg_dict)
    
    # Format authors for APA
    if len(authors) == 0:
        author_str = "Unknown"
    elif len(authors) == 1:
        author_str = authors[0]['name']
    elif len(authors) == 2:
        author_str = f"{authors[0]['name']} & {authors[1]['name']}"
    else:
        # For more than 2 authors, use first author et al.
        author_str = f"{authors[0]['name']} et al."
    
    # Build APA citation
    apa = f"{author_str} ({year}). "
    apa += f"<em>{pkg_dict.get('title', 'Untitled Dataset')}</em> [Data set]. "
    apa += f"{pkg_dict.get('doi_publisher', toolkit.config.get('ckanext.doi.publisher', 'Unknown Publisher'))}"
    
    if doi_url:
        apa += f". {doi_url}"
    
    return apa


def export_citation(pkg_dict, format_type):
    """
    Export citation in the specified format.
    
    Args:
        pkg_dict: Package dictionary
        format_type: Citation format ('bibtex', 'ris', 'endnote', 'apa')
    
    Returns:
        Formatted citation string
    """
    format_functions = {
        'bibtex': export_bibtex,
        'ris': export_ris,
        'endnote': export_endnote,
        'apa': export_apa
    }
    
    if format_type not in format_functions:
        raise ValueError(f"Unsupported citation format: {format_type}")
    
    return format_functions[format_type](pkg_dict)


def get_citation_mimetype(format_type):
    """Get the appropriate MIME type for the citation format."""
    mimetypes = {
        'bibtex': 'application/x-bibtex',
        'ris': 'application/x-research-info-systems',
        'endnote': 'application/x-endnote-refer',
        'apa': 'text/plain'
    }
    return mimetypes.get(format_type, 'text/plain')


def get_citation_filename(pkg_dict, format_type):
    """Generate an appropriate filename for the citation export."""
    base_name = pkg_dict.get('name', pkg_dict.get('id', 'dataset'))
    extensions = {
        'bibtex': 'bib',
        'ris': 'ris',
        'endnote': 'enw',
        'apa': 'txt'
    }
    extension = extensions.get(format_type, 'txt')
    return f"{base_name}_citation.{extension}"
