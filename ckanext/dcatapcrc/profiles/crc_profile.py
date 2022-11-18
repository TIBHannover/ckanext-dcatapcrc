# encoding: utf-8

from rdflib.namespace import Namespace
from rdflib import URIRef, RDF, RDFS, Literal
from ckanext.dcat.profiles import RDFProfile
from ckanext.dcatapcrc.libs.helpers import Helper
from ckanext.dcat.profiles import CleanedURIRef
from ckanext.dcat.utils import resource_uri


DC = Namespace("http://purl.org/dc/terms/")
DC_ITEMTYPES = Namespace("http://purl.org/dc/dcmitype/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
SCHEMAORG = Namespace("https://schema.org/")
EMMO = Namespace("http://emmo.info/emmo/")
TEMA = Namespace("https://www.tib.eu/tema/")
ENVO = Namespace("http://purl.obolibrary.org/obo/envo/")
NCIT = Namespace("http://purl.obolibrary.org/obo/ncit/")


class CRCDCATAPProfile(RDFProfile):
    '''
        An RDF profile for the Swedish DCAT-AP recommendation for data portals

        It requires the European DCAT-AP profile (`euro_dcat_ap`)
    '''

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        g = self.g
        
        g.bind("SCHEMAORG", SCHEMAORG)
        g.bind("EMMO", EMMO)
        g.bind("dc", DC_ITEMTYPES)
        g.bind("TEMA", TEMA)
        g.bind("ENVO", ENVO)
        g.bind("NCIT", NCIT)

                
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
            
            ## add samples ##
            linked_samples = Helper.get_linked_samples(resource_dict['id'])
            for sample_name, sample_link in linked_samples.items():
                dc_physical_object = URIRef("http://purl.org/dc/dcmitype/PhysicalObject")
                sample = CleanedURIRef(sample_link)
                g.add((distribution, dc_physical_object, sample))
            
            ## add matarial ##
            if resource_dict.get("material_combination"):
                emmo_material = URIRef("http://emmo.info/emmo/Material") 
                g.add((distribution, emmo_material, Literal(resource_dict.get("material_combination"))))
            
            ## add surface preparation ##
            if resource_dict.get("surface_preparation"):
                tema_sfp = URIRef("https://www.tib.eu/tema/surfacePreparation") 
                g.add((distribution, tema_sfp, Literal(resource_dict.get("surface_preparation"))))
            
            ## add atmosphere ##
            if resource_dict.get("atmosphere"):
                envo_atmosphere = URIRef("http://purl.obolibrary.org/obo/envo/atmosphere") 
                g.add((distribution, envo_atmosphere, Literal(resource_dict.get("atmosphere"))))
                

            ## add data_type ##
            if resource_dict.get("data_type"):
                ncit_dataType = URIRef("http://purl.obolibrary.org/obo/ncit/ScientificDataType") 
                g.add((distribution, ncit_dataType, Literal(resource_dict.get("data_type"))))