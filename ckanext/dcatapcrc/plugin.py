import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint
from ckanext.dcatapcrc.controller import BaseController


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

    def after_create(self, context, pkg_dict):
        return pkg_dict

    def after_update(self, context, pkg_dict):
        return pkg_dict

    def after_show(self, context, pkg_dict):
        return pkg_dict

    def before_search(self, search_params):
        return search_params

    def before_index(self, pkg_dict):
        return pkg_dict

    def before_view(self, pkg_dict):
        return pkg_dict