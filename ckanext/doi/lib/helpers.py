# !/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

import json
from datetime import datetime

import dateutil.parser as parser
from ckan.plugins import toolkit
from ckantools.config import get_debug, get_setting


def package_get_year(pkg_dict):
    """
    Helper function to return the package year published.

    :param pkg_dict: return:
    """
    if not isinstance(pkg_dict['metadata_created'], datetime):
        pkg_dict['metadata_created'] = parser.parse(pkg_dict['metadata_created'])

    return pkg_dict['metadata_created'].year


def get_site_title():
    """
    Helper function to return the config site title, if it exists.

    :returns: str site title
    """
    return toolkit.config.get('ckanext.doi.site_title')


def get_site_url():
    """
    Get the site URL.

    Try and use ckanext.doi.site_url but if that's not set use ckan.site_url.
    """
    site_url = toolkit.config.get(
        'ckanext.doi.site_url', toolkit.config.get('ckan.site_url', '')
    )
    return site_url.rstrip('/')


def date_or_none(date_object_or_string):
    """
    Try and convert the given object into a datetime; if not possible, return None.

    :param date_object_or_string: a datetime or date string
    :return: datetime or None
    """
    if isinstance(date_object_or_string, datetime):
        return date_object_or_string
    elif isinstance(date_object_or_string, str):
        return parser.parse(date_object_or_string)
    else:
        return None


def doi_test_mode():
    """
    Determines whether we're running in test mode.

    :return: bool
    """
    return toolkit.asbool(get_setting('ckanext.doi.test_mode', default=get_debug()))


def get_doi_platform():
    """
    Get name of the Platform that is being used for DOI creation

    :return: string
    """

    return toolkit.config.get('ckanext.doi.platform', 'datacite')


def parse_json_authors(authors_json):
    """
    Helper function to parse JSON authors field in templates.

    Normalizes common author shapes into a list of dicts with "name" and
    optional "given_name", "family_name", "orcid", "affiliation".

    :param authors_json: JSON string, list, dict, or string of authors
    :return: list of author dictionaries or empty list
    """
    if not authors_json:
        return []

    try:
        if isinstance(authors_json, str):
            authors = json.loads(authors_json)
        elif isinstance(authors_json, list):
            authors = authors_json
        elif isinstance(authors_json, dict):
            authors = [authors_json]
        else:
            return []
    except (json.JSONDecodeError, TypeError, ValueError):
        return []

    normalized = []
    for author in authors:
        if isinstance(author, str):
            name = author.strip()
            if name:
                normalized.append({'name': name})
            continue

        if not isinstance(author, dict):
            continue

        given_name = author.get('given_name') or author.get('given') or author.get('first_name')
        family_name = author.get('family_name') or author.get('family') or author.get('last_name')
        name = author.get('name') or author.get('full_name')

        if not name:
            if given_name and family_name:
                name = f'{given_name} {family_name}'
            elif family_name:
                name = family_name
            elif given_name:
                name = given_name

        if not name:
            continue

        orcid = author.get('orcid') or author.get('ORCID') or author.get('orcid_id')
        if isinstance(orcid, str):
            orcid = orcid.strip()
            if 'orcid.org/' in orcid:
                orcid = orcid.split('orcid.org/')[-1]

        affiliation = author.get('affiliation') or author.get('affiliations')
        if isinstance(affiliation, list):
            if affiliation:
                first = affiliation[0]
                if isinstance(first, dict):
                    affiliation = first.get('name') or first.get('affiliation')
                else:
                    affiliation = first
            else:
                affiliation = None
        elif isinstance(affiliation, dict):
            affiliation = affiliation.get('name') or affiliation.get('affiliation')

        author_dict = {'name': name}
        if given_name:
            author_dict['given_name'] = given_name
        if family_name:
            author_dict['family_name'] = family_name
        if orcid:
            author_dict['orcid'] = orcid
        if affiliation:
            author_dict['affiliation'] = affiliation
        email = author.get('email') or author.get('mail')
        if email:
            author_dict['email'] = email

        normalized.append(author_dict)

    return normalized
