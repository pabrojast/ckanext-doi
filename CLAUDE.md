# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `ckanext-doi`, a CKAN extension that assigns Digital Object Identifiers (DOIs) to datasets using the DataCite/Crossref DOI service. The extension automatically creates DOIs for new datasets and registers them with DataCite/Crossref when datasets become active and public.

## Development Commands

### Testing
- **Run tests against CKAN 2.9.x**: `docker compose run latest`
- **Run tests against CKAN 2.10.x**: `docker compose run next`
- **Build Docker images**: `docker compose build`

The test configuration uses Docker Compose with services for CKAN, PostgreSQL, Solr, and Redis. Tests mock the DataCite API and don't require internet connection or credentials.

### DOI Management Commands
- **Delete all DOIs from database**: `ckan -c $CONFIG_FILE doi delete-dois`
- **Update DOI metadata for all packages**: `ckan -c $CONFIG_FILE doi update-doi`
- **Update DOI metadata for specific package**: `ckan -c $CONFIG_FILE doi update-doi -p PACKAGE_ID`

### Database Migration
- **Initialize DOI database tables**: `ckan -c $CONFIG_FILE db upgrade -p doi`

## Architecture

### Core Components

**Plugin Entry Point**: `ckanext.doi.plugin:DOIPlugin` - Main plugin class implementing CKAN interfaces
- `IConfigurer`: Template directory configuration
- `IPackageController`: Dataset lifecycle hooks for DOI creation/updating
- `ITemplateHelpers`: Helper functions for templates
- `IClick`: CLI command registration

**Key Modules**:
- `ckanext/doi/lib/metadata.py`: Metadata extraction and XML generation for DataCite/Crossref schemas
- `ckanext/doi/lib/api.py`: DataCite/Crossref API client implementations
- `ckanext/doi/model/`: Database models and CRUD operations for DOI records
- `ckanext/doi/cli.py`: Command-line interface for DOI management
- `ckanext/doi/interfaces.py`: IDoi interface for extending metadata building

### DOI Workflow

1. **Dataset Creation**: New datasets automatically get assigned a DOI (stored locally)
2. **Publication**: When dataset becomes active and public, DOI is registered with DataCite/Crossref
3. **Updates**: Metadata changes trigger updates to registered DOIs
4. **Display**: DOI information is injected into package dictionaries for template display

### Supported Platforms

- **DataCite**: Primary DOI provider (default)
- **Crossref**: Alternative DOI provider
- Platform is configurable via `ckanext.doi.platform` setting

### Extension Points

**IDoi Interface**: Plugins can implement `build_metadata_dict()` and `build_xml_dict()` methods to customize:
- Metadata extraction from package dictionaries
- XML structure for DOI registration
- Error handling for missing required fields

### Configuration Requirements

**Required Settings**:
- `ckanext.doi.account_name`: DataCite/Crossref account name
- `ckanext.doi.account_password`: Account password  
- `ckanext.doi.prefix`: DOI prefix from your account
- `ckanext.doi.publisher`: Institution name
- `ckanext.doi.test_mode`: Enable test/development mode

**Optional Settings**:
- `ckanext.doi.platform`: DOI platform (datacite/crossref, default: datacite)
- `ckanext.doi.disable_on_update`: Disable automatic DOI minting on dataset updates
- `ckanext.doi.site_url`: Custom site URL for DOI links
- `ckanext.doi.site_title`: Site title for citations

### Template Integration

The extension provides citation snippets:
- `doi/snippets/package_citation.html`: Full dataset citation
- `doi/snippets/resource_citation.html`: Individual resource citation

Templates receive DOI data via injected package dictionary fields:
- `doi`: DOI identifier
- `doi_status`: Publication status (boolean)
- `doi_date_published`: Publication date
- `doi_publisher`: Publisher name