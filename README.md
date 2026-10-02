# ckanext-dcatapcrc

[![Tests](https://github.com/TIBHannover/ckanext-dcatapcrc/actions/workflows/test.yml/badge.svg)](https://github.com/TIBHannover/ckanext-dcatapcrc/actions/workflows/test.yml)

`ckanext-dcatapcrc` adds the CRC/SFB 1368 RDF profile to CKAN's DCAT output
and keeps dataset metadata synchronized with an Apache Jena SPARQL endpoint.
It also provides a sysadmin catalog page for exporting the complete catalog or
queueing bulk push and delete jobs.

## Compatibility

| CKAN version | Status |
| --- | --- |
| 2.11 | Supported and tested with Python 3.10 |
| 2.10 | Supported and tested with Python 3.10 |
| 2.9 and earlier | Not supported |

The package requires Python 3.9 or newer and uses `ckanext-dcat` 2.4.4. The
`euro_dcat_ap_2` profile remains the base profile so existing RDF output is not
silently switched to DCAT-AP 3.

## Behavior

- Registers the `crc_dcat_ap` RDF profile and the `dcat_crc` CKAN plugin.
- Adds CRC publication, equipment, sample, material, preparation, atmosphere,
  data type, and analysis-method triples to dataset RDF.
- Inserts dataset RDF into Jena after dataset creation.
- Replaces the existing graph after dataset or resource updates.
- Removes matching triples after dataset or resource deletion.
- Adds a sysadmin-only **Catalog** page with Turtle export and queued bulk
  synchronization actions.
- Continues CKAN writes if Jena or an optional linked-metadata integration is
  unavailable, while logging the failure for operators.

The optional `dataset_reference`, `machine_link`, and `sample_link` plugins add
their linked metadata when installed and enabled. Their absence does not stop
the DCAT profile from loading.

## Installation

1. Activate the CKAN virtual environment.
2. Clone and install the extension and its dependencies:

       git clone https://github.com/TIBHannover/ckanext-dcatapcrc.git
       cd ckanext-dcatapcrc
       pip install -r requirements.txt
       pip install -e .

3. Add the base DCAT plugin and this extension to `ckan.plugins`:

       ckan.plugins = ... dcat dcat_crc

4. Configure the RDF profile chain and Jena update endpoint:

       ckanext.dcat.rdf.profiles = euro_dcat_ap_2 crc_dcat_ap
       ckanext.apachejena.endpoint = https://jena.example.test/dataset/update

   The profile chain is set to the value above by default when no explicit
   `ckanext.dcat.rdf.profiles` setting exists. Without a Jena endpoint, RDF
   serialization and catalog export still work, but synchronization is skipped.
   The equivalent environment variable is `CKANEXT__APACHEJENA__ENDPOINT`.
   The previous `ckanext.apacheJena.endpoint` spelling is deprecated but remains
   supported for backward compatibility.

5. Ensure a CKAN worker is running for the bulk jobs, then restart CKAN and the
   web server.

No database migration is required by this extension.

## Administration

Sysadmins can open `/dcatapcrc/load_admin_view` to:

- download the active catalog as `ckan-catalog.ttl`;
- enqueue a refresh of all active dataset graphs in Jena; or
- enqueue deletion of all active dataset graphs from Jena.

The bulk actions use CKAN's background job queue. Dataset and resource lifecycle
callbacks synchronize the affected dataset directly.

## Development and tests

Install development requirements in a CKAN environment:

    pip install -r requirements.txt
    pip install -r dev-requirements.txt
    pip install -e .
    pytest --ckan-ini=test.ini --cov=ckanext.dcatapcrc ckanext/dcatapcrc

GitHub Actions runs the suite against CKAN 2.10 and 2.11. For a local container
matching CI, use `docker-compose.ci.yml` and select the version through
`CKAN_IMAGE`, `CKAN_VERSION`, and `SOLR_IMAGE`.

## License

[GNU Affero General Public License v3.0](LICENSE)
