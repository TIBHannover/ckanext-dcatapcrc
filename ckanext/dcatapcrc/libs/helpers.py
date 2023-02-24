# encoding: utf-8

from os import link
import ckan.plugins.toolkit as toolkit
from sqlalchemy.sql.expression import false
from SPARQLWrapper import SPARQLWrapper, POST
from ckanext.dcat.processors import RDFSerializer
from SPARQLWrapper import SPARQLWrapper, POST


SPARQL_ENDPOINT = "http://sparql11.test.service.tib.eu/fuseki/TestCKAN/update"
 
def check_plugin_enabled(plugin_name):
        '''
            Check a plugin is enabled in the target ckan instance or not.
        '''
        
        plugins = toolkit.config.get("ckan.plugins")
        if plugin_name in plugins:
            return True
        return False


if check_plugin_enabled("dataset_reference"):
    from ckanext.dataset_reference.models.package_reference_link import PackageReferenceLink
if check_plugin_enabled("semantic_media_wiki"):
    from ckanext.semantic_media_wiki.libs.media_wiki import Helper as mediaWikiHelper
if check_plugin_enabled("sample_link"):
    from ckanext.semantic_media_wiki.libs.sample_link import SampleLinkHelper



class Helper():

    def get_linked_publication(dataset_name):
        '''
            The functions get all the linked publications for a dataset in ckan.

            Args:
                - dataset_name: The target dataset name.
            Returns:
                - The publication citation
        '''

        if not check_plugin_enabled("dataset_reference"):
            return None
        
        linked_pubs = []
        res_object = PackageReferenceLink({})
        result = res_object.get_by_package(name=dataset_name)        
        if result != false:
            for res in result:
                linked_pubs.append(res.citation)
            
        return linked_pubs
    

    @staticmethod
    def get_linked_machines(resource_id):
        if not check_plugin_enabled("semantic_media_wiki"):
            return {}
        # a dict of machines [machine_name:machine_link]
        return mediaWikiHelper.get_machine_link(resource_id)        
    

    @staticmethod
    def get_linked_samples(resource_id):
        if not check_plugin_enabled("sample_link"):
            return {}
        
        # a dict of samples [sample_name:sample_link]
        return SampleLinkHelper.get_sample_link(resource_id)
    

    @staticmethod
    def insert_to_sparql(graph):
        for s,p,o in graph:
            s,p,o = Helper.clean_triples(s,p,o)
            query = 'INSERT DATA{ ' + s + ' ' + p + ' ' + o + ' .  }'            
            sparql = SPARQLWrapper(SPARQL_ENDPOINT)                        
            sparql.setMethod(POST)
            sparql.setQuery(query)
            results = sparql.query() 

        return results


    @staticmethod
    def delete_from_sparql(graph):
        for s,p,o in graph:
            s,p,o = Helper.clean_triples(s,p,o)
            query = ""           
            if "_:N" in o:
                # blank node as object
                query = 'DELETE{ ' + s + ' ' + p + ' ?bnode . ?bnode ?p ?o .} WHERE{ '  + s + ' ' + p + ' ?bnode . ?bnode ?p ?o . FILTER (isBlank(?bnode))}'
                sparql = SPARQLWrapper(SPARQL_ENDPOINT)                        
                sparql.setMethod(POST)
                sparql.setQuery(query)
                results = sparql.query()
            elif "_:N" not in s and "_:N" not in p:
                query = 'DELETE WHERE{ ' + s + ' ' + p + ' ?anything .  }'
                sparql = SPARQLWrapper(SPARQL_ENDPOINT)                        
                sparql.setMethod(POST)
                sparql.setQuery(query)
                results = sparql.query()
            
            print(query)             

        return results


    @staticmethod
    def get_dataset_graph(dataset_dict):
        dataset_dict = Helper.setDatasetUri(dataset_dict)
        serializer = RDFSerializer(profiles=dataset_dict.get('profiles'))
        gr_dataset = serializer.graph_from_dataset(dataset_dict)        
        return  serializer.g


    @staticmethod
    def clean_triples(s,p,o):
        if "http" in s:
            s = "<" + s + ">"
        if "http" in p:
            p = "<" + p + ">"
        if "http" in o:
            o = "<" + o + ">"
        if "http" not in o:
            o = "'" + o + "'"
        if s[0] == "N":
            s = '_:' + s            
        if o[0] == "N":
            o = '_:' + o 

        o = o.replace('\\', '\\\\')              
        
        return [s,p,o]
    


    @staticmethod
    def setDatasetUri(package):
        print(package)
        ckan_root_path = toolkit.config.get('ckan.root_path')
        ckan_base_url = toolkit.config.get('ckan.site_url')
        if ckan_root_path:
            ckan_root_path = ckan_root_path.split("/{{LANG}}")[0]
            package["uri"] = ckan_base_url + ckan_root_path + "/dataset/" + package['id']
            for res in package['resources']:
                res["uri"] = ckan_base_url + ckan_root_path + "/dataset/" + package['name'] + "/resource/" + res['id']
        else:
            package["uri"] = ckan_base_url + "/dataset/" + package['id']
            for res in package['resources']:
                res["uri"] = ckan_base_url + "/dataset/" + package['name'] + "/resource/" + res['id']
        
        return package
