#!/usr/bin/env python3
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

from flask import Blueprint, request, make_response
from ckan.plugins import toolkit
from ckan.common import config
from ckanext.doi.lib.citation_export import (
    export_citation, 
    get_citation_mimetype, 
    get_citation_filename
)

# Create blueprint
doi_blueprint = Blueprint('doi', __name__)


@doi_blueprint.route('/dataset/<id>/export_citation')
def export_citation_view(id):
    """
    Export citation for a dataset in various formats.
    
    Query parameters:
        format: Citation format (bibtex, ris, endnote, apa)
    """
    try:
        # Get the dataset
        context = {'for_view': True, 'user': toolkit.g.user, 'auth_user_obj': toolkit.g.userobj}
        pkg_dict = toolkit.get_action('package_show')(context, {'id': id})
        
        # Get the requested format
        format_type = request.args.get('format', 'bibtex').lower()
        
        # Export the citation
        citation_content = export_citation(pkg_dict, format_type)
        
        # Create response
        response = make_response(citation_content)
        response.headers['Content-Type'] = get_citation_mimetype(format_type)
        response.headers['Content-Disposition'] = f'attachment; filename="{get_citation_filename(pkg_dict, format_type)}"'
        
        return response
        
    except toolkit.ObjectNotFound:
        toolkit.abort(404, 'Dataset not found')
    except ValueError as e:
        toolkit.abort(400, str(e))
    except Exception as e:
        toolkit.abort(500, f'Error exporting citation: {str(e)}')


def get_blueprints():
    """Return the blueprint for this plugin."""
    return [doi_blueprint]