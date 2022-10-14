# encoding: utf-8

from rdflib.namespace import Namespace
from rdflib import BNode, URIRef, RDF, RDFS, Literal
from ckanext.dcat.profiles import RDFProfile

DCT = Namespace("http://purl.org/dc/terms/")


class CRCDCATAPProfile(RDFProfile):
    '''
    An RDF profile for the Swedish DCAT-AP recommendation for data portals

    It requires the European DCAT-AP profile (`euro_dcat_ap`)
    '''

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        g = self.g

        ref = URIRef("http://localhost:5000/some_concept")
        g.add((dataset_ref, DCT.hasPublication, ref ))
        g.add((ref, RDF.type, DCT.publication))
        g.add((ref, RDFS.label, Literal('Jonathan R. Diamond and Joseph V. Bonventre and Morris J. Karnovsky, "A role for oxygen free radicals in aminonucleoside nephrosis", Elsevier BV. Kidney International., vol. 29, pp. 478--483, feb 1986.')))
