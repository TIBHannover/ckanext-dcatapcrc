import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint
from ckanext.dcatapcrc.controller import BaseController
from ckanext.dcat.processors import RDFSerializer
from xml.etree import ElementTree
from SPARQLWrapper import SPARQLWrapper, POST


SPARQL_ENDPOINT = "http://sparql11.test.service.tib.eu/fuseki/TestCKAN/update"


class DcatapcrcPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IPackageController)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('public/statics', 'ckanext-dcatapcrc')


    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__) 
        blueprint.add_url_rule(
            u'/dcatapcrc/load_admin_view',
            u'load_admin_view',
            BaseController.load_admin_view,
            methods=['GET']
            )   
        
        blueprint.add_url_rule(
            u'/dcatapcrc/export_catalog',
            u'export_catalog',
            BaseController.export_catalog,
            methods=['GET']
            )   
        
        return blueprint 
    

    # IPackageController

    
    def after_create(self, context, pkg_dict):
        '''
            Post the dataset metadata to the sparql endpoint
        '''

        serializer = RDFSerializer(profiles=pkg_dict.get('profiles'))
        rdf_output = serializer.serialize_dataset(pkg_dict, _format="rdf")                                                
        childNodeList = ElementTree.fromstring(rdf_output.decode('utf-8'))
        for node in childNodeList:                     
            print(node)


        return pkg_dict

    
    def after_update(self, context, pkg_dict):
        '''
            Upadte an existing dataset metadata on the sparql endpoint
        '''

        # print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        # print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        # print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        # print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")

        serializer = RDFSerializer(profiles=pkg_dict.get('profiles'))        
        gr_dataset = serializer.graph_from_dataset(pkg_dict)                        
        graph = serializer.g        
        for s,p,o in graph:
            # print(s,p,o)
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

            
            query = 'INSERT DATA{ ' + s + ' ' + p + ' ' + o + ' .  }'            
            sparql = SPARQLWrapper(SPARQL_ENDPOINT)                        
            sparql.setMethod(POST)
            sparql.setQuery(query)
            results = sparql.query()            
        return pkg_dict
    
    
    def after_search(self, search_results, search_params):        
        return search_results

    def after_delete(self, context, pkg_dict):
        return pkg_dict
    
    def read(self, entity):
        return entity

    def create(self, entity):
        return entity

    def edit(self, entity):
        return entity

    def delete(self, entity):
        return entity

    def after_show(self, context, pkg_dict):
        return pkg_dict

    def before_search(self, search_params):
        return search_params

    def before_index(self, pkg_dict):
        return pkg_dict

    def before_view(self, pkg_dict):
        return pkg_dict