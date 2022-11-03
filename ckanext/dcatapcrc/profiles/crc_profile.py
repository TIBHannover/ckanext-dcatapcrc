# encoding: utf-8

from rdflib.namespace import Namespace
from rdflib import BNode, URIRef, RDF, RDFS, Literal
from ckanext.dcat.profiles import RDFProfile
from ckanext.dcatapcrc.libs.helpers import Helper

DCT = Namespace("http://purl.org/dc/terms/")
SCHEMAORG = Namespace("https://schema.org/")
NCIT = Namespace('http://purl.obolibrary.org/obo/')


class CRCDCATAPProfile(RDFProfile):
    '''
        An RDF profile for the Swedish DCAT-AP recommendation for data portals

        It requires the European DCAT-AP profile (`euro_dcat_ap`)
    '''

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        g = self.g
        g.bind("SCHEMAORG", SCHEMAORG)
        g.bind("NCIT", NCIT)

        # add linked publication(s)
        linked_publications = Helper.get_linked_publication(dataset_dict['name'])        
        if len(linked_publications) != 0:
            for citation in linked_publications:
                schema_org_ref = URIRef("https://schema.org/publication")
                
                ncit_citation_ref = BNode()
                 
                g.add((ncit_citation_ref, RDF.type, NCIT.citation))

                g.add((dataset_ref, schema_org_ref, ncit_citation_ref))

                g.add((ncit_citation_ref, RDFS.label, Literal(citation)))

                                
        


        
        
        
