# encoding: utf-8

from os import link
import ckan.plugins.toolkit as toolkit
from sqlalchemy.sql.expression import false

 
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
        if result != false and len(result) != 0:
            for res in result:
                linked_pubs.append(res.citation)
            
        return linked_pubs
    

    @staticmethod
    def get_linked_machines(resource_id):
        if not check_plugin_enabled("semantic_media_wiki"):
            return {}
        # a dict of machines [machine_name:machine_link]
        machines_dict = mediaWikiHelper.get_machine_link(resource_id)
        return machines_dict

    

