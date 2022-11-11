# encoding: utf-8

from rdflib.namespace import Namespace, SKOS
from rdflib import BNode, URIRef, RDF, RDFS, Literal
from ckanext.dcat.profiles import RDFProfile
from ckanext.dcatapcrc.libs.helpers import Helper
from ckanext.dcat.profiles import CleanedURIRef
from ckanext.dcat.utils import resource_uri


DCT = Namespace("http://purl.org/dc/terms/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
SCHEMAORG = Namespace("https://schema.org/")
EMMO = Namespace("http://emmo.info/emmo/")


class CRCDCATAPProfile(RDFProfile):
    '''
        An RDF profile for the Swedish DCAT-AP recommendation for data portals

        It requires the European DCAT-AP profile (`euro_dcat_ap`)
    '''

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        g = self.g
        
        g.bind("SCHEMAORG", SCHEMAORG)
        g.bind("EMMO", EMMO)
                
        ## add linked publication(s) ##
        linked_publications = Helper.get_linked_publication(dataset_dict['name'])        
        if len(linked_publications) != 0:
            for citation in linked_publications:
                schema_org_citation = URIRef("https://schema.org/citation")
                g.add((dataset_ref, schema_org_citation, Literal(citation)))


        for resource_dict in dataset_dict.get('resources', []):

            distribution = CleanedURIRef(resource_uri(resource_dict))

             ## add machines ##
            linked_machines = Helper.get_linked_machines(resource_dict['id'])
            if len(linked_machines.keys()) == 0:
                continue
            for machine_name, machine_url in linked_machines.items():
                emmo_device = URIRef("http://emmo.info/emmo/Device")
                machine = CleanedURIRef(machine_url)
                g.add((distribution, emmo_device, machine))
                

