#!/usr/bin/env python3
# encoding: utf-8
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

from datetime import datetime
from logging import getLogger
from typing import Any

from ckan.plugins import SingletonPlugin, implements, interfaces, toolkit

from ckanext.doi import cli
from ckanext.doi.lib.api import DataciteClient, get_client
from ckanext.doi.lib.helpers import (
    get_site_title,
    get_site_url,
    package_get_year,
    doi_test_mode,
    get_doi_platform,
    parse_json_authors,
)
from ckanext.doi.lib.metadata import build_metadata_dict, build_xml_dict, compute_metadata_hash
from ckanext.doi.model.crud import DOIQuery
from ckanext.doi.views import get_blueprints

log = getLogger(__name__)


class DOIPlugin(SingletonPlugin, toolkit.DefaultDatasetForm):
    """
    CKAN DOI Extension.
    """

    implements(interfaces.IConfigurer)
    implements(interfaces.IPackageController, inherit=True)
    implements(interfaces.ITemplateHelpers, inherit=True)
    implements(interfaces.IClick)
    implements(interfaces.IBlueprint)

    ## IClick
    def get_commands(self):
        return cli.get_commands()

    ## IConfigurer
    def update_config(self, config):
        """
        Adds templates.
        """
        toolkit.add_template_directory(config, 'theme/templates')

    ## IPackageController
    def after_dataset_create(self, context, pkg_dict):
        """
        A new dataset has been created, so we need to create a new DOI.

        NB: This hook fires *during* `package_create`, before CKAN's own
        `model.repo.commit()`. Inserting a row into `doi` here can race with
        the package row reaching the database — when callers create the DOI
        themselves after `package_create` returns, they should pass
        `_skip_doi_create=True` in the action context so we don't trigger
        the in-hook insert and risk a foreign-key violation.
        """
        if self._is_background_internal_update(context) or (context or {}).get('_skip_doi_create'):
            log.debug('Skipping in-hook DOI creation due to context flag')
            return pkg_dict
        DOIQuery.read_package(pkg_dict['id'], create_if_none=True)
        return pkg_dict

    ## IPackageController
    def after_dataset_update(self, context, pkg_dict):
        """
        Dataset has been created/updated.

        Check status of the dataset to determine if we should publish DOI to datacite
        network.
        """
        if self._is_background_internal_update(context):
            log.debug('Skipping DOI update for internal background metadata update')
            return pkg_dict

        # Is this active and public? If so we need to make sure we have an active DOI
        if not toolkit.config.get('ckanext.doi.disable_on_update', False) and pkg_dict.get(
            'state', 'active') == 'active' and not pkg_dict.get(
            'private', False
        ):
            package_id = pkg_dict['id']

            # remove user-defined update schemas first (if needed)
            context.pop('schema', None)

            # Load the package_show version of the dict
            pkg_show_dict = toolkit.get_action('package_show')(
                context, {'id': package_id}
            )

            # Load or create the local DOI (package may not have a DOI if extension was loaded
            # after package creation)
            doi = DOIQuery.read_package(package_id, create_if_none=True)

            metadata_dict: dict[str, Any] = build_metadata_dict(pkg_show_dict)

            # Compute a stable hash of the meaningful metadata to detect real changes
            platform = toolkit.config.get('ckanext.doi.platform', 'datacite')
            metadata_hash = compute_metadata_hash(metadata_dict, platform)

            # Skip update if metadata hasn't actually changed
            if doi.published is not None and doi.metadata_hash == metadata_hash:
                log.debug(
                    f'DOI {doi.identifier} metadata unchanged (hash match), skipping update'
                )
                return pkg_dict

            xml_dict = build_xml_dict(metadata_dict)

            client = get_client()

            if doi.published is None:
                # metadata gets created before minting
                client.set_metadata(doi.identifier, xml_dict)
                client.mint_doi(doi.identifier, package_id)
                DOIQuery.update_doi(doi.identifier, metadata_hash=metadata_hash)
                self._flash_success_safe(toolkit._('%(platform)s DOI created') % {'platform': client.client_name})
            else:
                same = client.check_for_update(doi.identifier, xml_dict)
                if not same:
                    # Not the same, so we want to update the metadata
                    client.set_metadata(doi.identifier, xml_dict)
                    DOIQuery.update_doi(doi.identifier, metadata_hash=metadata_hash)
                    self._flash_success_safe(toolkit._('%(platform)s DOI metadata updated') % {'platform': client.client_name})

        return pkg_dict

    def _is_background_internal_update(self, context):
        context = context or {}
        return bool(
            context.get('_schemingdcat_metadata_job') or
            context.get('_skip_doi_update')
        )

    def _flash_success_safe(self, message):
        """
        Flash helpers require a request context and a configured secret_key.
        Background updates (jobs/threads) should not attempt UI flashes.
        """
        try:
            from flask import has_request_context, current_app
            if not has_request_context():
                log.debug('Skipping flash_success outside request context')
                return
            if not getattr(current_app, 'secret_key', None):
                log.warning('Skipping flash_success because app.secret_key is empty')
                return
        except Exception as e:
            log.debug(f'Skipping flash_success due to context check error: {e}')
            return

        try:
            toolkit.h.flash_success(message)
        except Exception as e:
            log.warning(f'Could not flash DOI message: {e}')

    # IPackageController
    def after_dataset_show(self, context, pkg_dict):
        """
        Add the DOI details to the pkg_dict so it can be displayed.
        """
        doi = DOIQuery.read_package(pkg_dict['id'])
        if doi:
            pkg_dict['doi'] = doi.identifier
            pkg_dict['doi_status'] = True if doi.published else False
            pkg_dict['domain'] = get_site_url().replace('http://', '')
            pkg_dict['doi_date_published'] = (
                datetime.strftime(doi.published, '%Y-%m-%d') if doi.published else None
            )
            pkg_dict['doi_publisher'] = toolkit.config.get('ckanext.doi.publisher')

    def after_create(self, *args, **kwargs):
        """
        CKAN 2.9 compat version of after_dataset_create.
        """
        return self.after_dataset_create(*args, **kwargs)

    def after_update(self, *args, **kwargs):
        """
        CKAN 2.9 compat version of after_dataset_update.
        """
        return self.after_dataset_update(*args, **kwargs)

    def after_show(self, *args, **kwargs):
        """
        CKAN 2.9 compat version of after_dataset_show.
        """
        return self.after_dataset_show(*args, **kwargs)

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'package_get_year': package_get_year,
            'now': datetime.now,
            'get_site_title': get_site_title,
            'doi_test_mode': doi_test_mode,
            'get_doi_platform': get_doi_platform,
            'parse_json_authors': parse_json_authors,
        }

    # IBlueprint
    def get_blueprint(self):
        """Return the blueprint for this plugin."""
        return get_blueprints()
