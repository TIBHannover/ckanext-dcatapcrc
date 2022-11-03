# encoding: utf-8

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
        
        res_object = PackageReferenceLink({})
        result = res_object.get_by_package(name=dataset_name)
        if result != false and len(result) != 0:
            return result.citation

        return None
    

