# encoding: utf-8

from rdflib.namespace import Namespace, SKOS, XSD
from rdflib import BNode, URIRef, RDF, RDFS, Literal
from ckanext.dcat.profiles import RDFProfile
from ckanext.dcatapcrc.libs.helpers import Helper
from ckanext.dcat.profiles import URIRefOrLiteral, CleanedURIRef
from ckanext.dcat.utils import resource_uri, publisher_uri_from_dataset_dict


DCT = Namespace("http://purl.org/dc/terms/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
ADMS = Namespace("http://www.w3.org/ns/adms#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace('http://schema.org/')
TIME = Namespace('http://www.w3.org/2006/time')
LOCN = Namespace('http://www.w3.org/ns/locn#')
GSP = Namespace('http://www.opengis.net/ont/geosparql#')
OWL = Namespace('http://www.w3.org/2002/07/owl#')
SPDX = Namespace('http://spdx.org/rdf/terms#')


namespaces = {
    'dct': DCT,
    'dcat': DCAT,
    'adms': ADMS,
    'vcard': VCARD,
    'foaf': FOAF,
    'schema': SCHEMA,
    'time': TIME,
    'skos': SKOS,
    'locn': LOCN,
    'gsp': GSP,
    'owl': OWL,
    'spdx': SPDX,
}


SCHEMAORG = Namespace("https://schema.org/")
EMMO = Namespace("http://emmo.info/emmo")


class CRCDCATAPProfile(RDFProfile):
    '''
        An RDF profile for the Swedish DCAT-AP recommendation for data portals

        It requires the European DCAT-AP profile (`euro_dcat_ap`)
    '''

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        g = self.g
        

        # g.bind("SCHEMAORG", SCHEMAORG)
        # g.bind("EMMO", EMMO)

        # # add linked publication(s)
        # linked_publications = Helper.get_linked_publication(dataset_dict['name'])        
        # if len(linked_publications) != 0:
        #     for citation in linked_publications:
        #         schema_org_citation = URIRef("https://schema.org/citation")
        #         g.add((dataset_ref, schema_org_citation, Literal(citation)))
        
        # # add machines
        # for res in dataset_dict['resources']:
        #     linked_machines = Helper.get_linked_machines(res['id'])
        #     if len(linked_machines.keys()) == 0:
        #         continue
        #     for machine_name, machine_url in linked_machines.iterrows():
        #         emmo_device = URIRef("http://emmo.info/emmo#EMMO_494b372c_cfdf_47d3_a4de_5e037c540de8")
        #         for dist in self._distributions(dataset_ref):

        for prefix, namespace in namespaces.items():
            g.bind(prefix, namespace)

        g.add((dataset_ref, RDF.type, DCAT.Dataset))

        # Basic fields
        items = [
            ('title', DCT.title, None, Literal),
            ('notes', DCT.description, None, Literal),
            ('url', DCAT.landingPage, None, URIRef),
            ('identifier', DCT.identifier, ['guid', 'id'], Literal),
            ('version', OWL.versionInfo, ['dcat_version'], Literal),
            ('version_notes', ADMS.versionNotes, None, Literal),
            ('frequency', DCT.accrualPeriodicity, None, URIRefOrLiteral),
            ('access_rights', DCT.accessRights, None, Literal),
            ('dcat_type', DCT.type, None, Literal),
            ('provenance', DCT.provenance, None, Literal),
        ]
        self._add_triples_from_dict(dataset_dict, dataset_ref, items)

        # Tags
        for tag in dataset_dict.get('tags', []):
            g.add((dataset_ref, DCAT.keyword, Literal(tag['name'])))

        # Dates
        items = [
            ('issued', DCT.issued, ['metadata_created'], Literal),
            ('modified', DCT.modified, ['metadata_modified'], Literal),
        ]
        self._add_date_triples_from_dict(dataset_dict, dataset_ref, items)

        #  Lists
        items = [
            ('language', DCT.language, None, URIRefOrLiteral),
            ('theme', DCAT.theme, None, URIRef),
            ('conforms_to', DCT.conformsTo, None, Literal),
            ('alternate_identifier', ADMS.identifier, None, Literal),
            ('documentation', FOAF.page, None, URIRefOrLiteral),
            ('related_resource', DCT.relation, None, URIRefOrLiteral),
            ('has_version', DCT.hasVersion, None, URIRefOrLiteral),
            ('is_version_of', DCT.isVersionOf, None, URIRefOrLiteral),
            ('source', DCT.source, None, Literal),
            ('sample', ADMS.sample, None, Literal),
        ]
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, items)

        # Contact details
        if any([
            self._get_dataset_value(dataset_dict, 'contact_uri'),
            self._get_dataset_value(dataset_dict, 'contact_name'),
            self._get_dataset_value(dataset_dict, 'contact_email'),
            self._get_dataset_value(dataset_dict, 'maintainer'),
            self._get_dataset_value(dataset_dict, 'maintainer_email'),
            self._get_dataset_value(dataset_dict, 'author'),
            self._get_dataset_value(dataset_dict, 'author_email'),
        ]):

            contact_uri = self._get_dataset_value(dataset_dict, 'contact_uri')
            if contact_uri:
                contact_details = CleanedURIRef(contact_uri)
            else:
                contact_details = BNode()

            g.add((contact_details, RDF.type, VCARD.Organization))
            g.add((dataset_ref, DCAT.contactPoint, contact_details))

            self._add_triple_from_dict(
                dataset_dict, contact_details,
                VCARD.fn, 'contact_name', ['maintainer', 'author']
            )
            # Add mail address as URIRef, and ensure it has a mailto: prefix
            self._add_triple_from_dict(
                dataset_dict, contact_details,
                VCARD.hasEmail, 'contact_email', ['maintainer_email',
                                                  'author_email'],
                _type=URIRef, value_modifier=self._add_mailto
            )

        # Publisher
        if any([
            self._get_dataset_value(dataset_dict, 'publisher_uri'),
            self._get_dataset_value(dataset_dict, 'publisher_name'),
            dataset_dict.get('organization'),
        ]):

            publisher_uri = publisher_uri_from_dataset_dict(dataset_dict)
            if publisher_uri:
                publisher_details = CleanedURIRef(publisher_uri)
            else:
                # No organization nor publisher_uri
                publisher_details = BNode()

            g.add((publisher_details, RDF.type, FOAF.Organization))
            g.add((dataset_ref, DCT.publisher, publisher_details))

            publisher_name = self._get_dataset_value(dataset_dict, 'publisher_name')
            if not publisher_name and dataset_dict.get('organization'):
                publisher_name = dataset_dict['organization']['title']

            g.add((publisher_details, FOAF.name, Literal(publisher_name)))
            # TODO: It would make sense to fallback these to organization
            # fields but they are not in the default schema and the
            # `organization` object in the dataset_dict does not include
            # custom fields
            items = [
                ('publisher_email', FOAF.mbox, None, Literal),
                ('publisher_url', FOAF.homepage, None, URIRef),
                ('publisher_type', DCT.type, None, URIRefOrLiteral),
            ]

            self._add_triples_from_dict(dataset_dict, publisher_details, items)

        # Temporal
        start = self._get_dataset_value(dataset_dict, 'temporal_start')
        end = self._get_dataset_value(dataset_dict, 'temporal_end')
        if start or end:
            temporal_extent = BNode()

            g.add((temporal_extent, RDF.type, DCT.PeriodOfTime))
            if start:
                self._add_date_triple(temporal_extent, SCHEMA.startDate, start)
            if end:
                self._add_date_triple(temporal_extent, SCHEMA.endDate, end)
            g.add((dataset_ref, DCT.temporal, temporal_extent))

        # Spatial
        spatial_uri = self._get_dataset_value(dataset_dict, 'spatial_uri')
        spatial_text = self._get_dataset_value(dataset_dict, 'spatial_text')
        spatial_geom = self._get_dataset_value(dataset_dict, 'spatial')

        if spatial_uri or spatial_text or spatial_geom:
            if spatial_uri:
                spatial_ref = CleanedURIRef(spatial_uri)
            else:
                spatial_ref = BNode()

            g.add((spatial_ref, RDF.type, DCT.Location))
            g.add((dataset_ref, DCT.spatial, spatial_ref))

            if spatial_text:
                g.add((spatial_ref, SKOS.prefLabel, Literal(spatial_text)))

            if spatial_geom:
                # GeoJSON
                g.add((spatial_ref,
                       LOCN.geometry,
                       Literal(spatial_geom, datatype=GEOJSON_IMT)))
                # WKT, because GeoDCAT-AP says so
                try:
                    g.add((spatial_ref,
                           LOCN.geometry,
                           Literal(wkt.dumps(json.loads(spatial_geom),
                                             decimals=4),
                                   datatype=GSP.wktLiteral)))
                except (TypeError, ValueError, InvalidGeoJSONException):
                    pass

        # Resources
        for resource_dict in dataset_dict.get('resources', []):

            distribution = CleanedURIRef(resource_uri(resource_dict))

            g.add((dataset_ref, DCAT.distribution, distribution))

            g.add((distribution, RDF.type, DCAT.Distribution))

            #  Simple values
            items = [
                ('name', DCT.title, None, Literal),
                ('description', DCT.description, None, Literal),
                ('status', ADMS.status, None, URIRefOrLiteral),
                ('rights', DCT.rights, None, URIRefOrLiteral),
                ('license', DCT.license, None, URIRefOrLiteral),
                ('access_url', DCAT.accessURL, None, URIRef),
                ('download_url', DCAT.downloadURL, None, URIRef),
            ]

            self._add_triples_from_dict(resource_dict, distribution, items)

            #  Lists
            items = [
                ('documentation', FOAF.page, None, URIRefOrLiteral),
                ('language', DCT.language, None, URIRefOrLiteral),
                ('conforms_to', DCT.conformsTo, None, Literal),
            ]
            self._add_list_triples_from_dict(resource_dict, distribution, items)

            # Format
            mimetype = resource_dict.get('mimetype')
            fmt = resource_dict.get('format')

            # IANA media types (either URI or Literal) should be mapped as mediaType.
            # In case format is available and mimetype is not set or identical to format,
            # check which type is appropriate.
            if fmt and (not mimetype or mimetype == fmt):
                if ('iana.org/assignments/media-types' in fmt
                        or not fmt.startswith('http') and '/' in fmt):
                    # output format value as dcat:mediaType instead of dct:format
                    mimetype = fmt
                    fmt = None
                else:
                    # Use dct:format
                    mimetype = None

            if mimetype:
                g.add((distribution, DCAT.mediaType,
                       URIRefOrLiteral(mimetype)))

            if fmt:
                g.add((distribution, DCT['format'],
                       URIRefOrLiteral(fmt)))


            # URL fallback and old behavior
            url = resource_dict.get('url')
            download_url = resource_dict.get('download_url')
            access_url = resource_dict.get('access_url')
            # Use url as fallback for access_url if access_url is not set and download_url is not equal
            if url and not access_url:
                if (not download_url) or (download_url and url != download_url):
                  self._add_triple_from_dict(resource_dict, distribution, DCAT.accessURL, 'url', _type=URIRef)

            # Dates
            items = [
                ('issued', DCT.issued, None, Literal),
                ('modified', DCT.modified, None, Literal),
            ]

            self._add_date_triples_from_dict(resource_dict, distribution, items)

            # Numbers
            if resource_dict.get('size'):
                try:
                    g.add((distribution, DCAT.byteSize,
                           Literal(float(resource_dict['size']),
                                   datatype=XSD.decimal)))
                except (ValueError, TypeError):
                    g.add((distribution, DCAT.byteSize,
                           Literal(resource_dict['size'])))
            # Checksum
            if resource_dict.get('hash'):
                checksum = BNode()
                g.add((checksum, RDF.type, SPDX.Checksum))
                g.add((checksum, SPDX.checksumValue,
                       Literal(resource_dict['hash'],
                               datatype=XSD.hexBinary)))

                if resource_dict.get('hash_algorithm'):
                    g.add((checksum, SPDX.algorithm,
                           URIRefOrLiteral(resource_dict['hash_algorithm'])))

                g.add((distribution, SPDX.checksum, checksum))
            

                                
        


        
        
        
