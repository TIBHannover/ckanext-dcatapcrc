# Changelog

## 1.0.0

- Add CKAN 2.10 and 2.11 package/resource controller callbacks while retaining
  compatibility aliases for older callback names.
- Support current and legacy Flask catalog-download arguments.
- Pin the supported `ckanext-dcat` 2.4.4 release and require Python 3.9+.
- Make CRC profile selection deterministic and preserve DCAT-AP 2 as the base.
- Improve optional integration and Jena failure handling and logging.
- Remove the unavailable jQuery UI webasset preload.
- Include the helper and RDF profile modules in built wheel distributions.
- Add behavior-focused tests and a CKAN 2.10/2.11 CI matrix.
