import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint
from ckanext.dcatapcrc.controller import BaseController


class DcatapcrcPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

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
        
        return blueprint 