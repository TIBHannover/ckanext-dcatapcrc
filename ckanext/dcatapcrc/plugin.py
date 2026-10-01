import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint

from ckanext.dcatapcrc.controller import BaseController
from ckanext.dcatapcrc.libs.helpers import Helper


log = logging.getLogger(__name__)


class DcatapcrcPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IPackageController)
    plugins.implements(plugins.IResourceController)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("public/statics", "ckanext-dcatapcrc")
        config_.setdefault(
            "ckanext.dcat.rdf.profiles",
            "euro_dcat_ap_2 crc_dcat_ap",
        )

    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.add_url_rule(
            "/dcatapcrc/load_admin_view",
            "load_admin_view",
            BaseController.load_admin_view,
            methods=["GET"],
        )
        blueprint.add_url_rule(
            "/dcatapcrc/export_catalog",
            "export_catalog",
            BaseController.export_catalog,
            methods=["GET"],
        )
        blueprint.add_url_rule(
            "/dcatapcrc/push_to_sparql",
            "push_to_sparql",
            BaseController.push_to_sparql,
            methods=["GET"],
        )
        blueprint.add_url_rule(
            "/dcatapcrc/delete_from_sparql",
            "delete_from_sparql",
            BaseController.delete_from_sparql,
            methods=["GET"],
        )
        return blueprint

    # IPackageController callbacks used by CKAN 2.10 and 2.11.

    def after_dataset_create(self, context, pkg_dict):
        try:
            package = self._package_show(pkg_dict["id"])
            Helper.insert_to_sparql(Helper.get_dataset_graph(package))
        except Exception:
            log.exception("Failed to insert CRC dataset metadata into SPARQL")
        return pkg_dict

    def after_dataset_update(self, context, pkg_dict):
        try:
            package = self._package_show(pkg_dict["id"])
            graph = Helper.get_dataset_graph(package)
            Helper.delete_from_sparql(graph)
            Helper.insert_to_sparql(graph)
        except Exception:
            log.exception("Failed to update CRC dataset metadata in SPARQL")
        return pkg_dict

    def after_dataset_delete(self, context, pkg_dict):
        try:
            package = self._package_show(pkg_dict["id"])
            Helper.delete_from_sparql(Helper.get_dataset_graph(package))
        except Exception:
            log.exception("Failed to delete CRC dataset metadata from SPARQL")
        return pkg_dict

    def after_dataset_search(self, search_results, search_params):
        return search_results

    def after_dataset_show(self, context, pkg_dict):
        return pkg_dict

    def before_dataset_search(self, search_params):
        return search_params

    def before_dataset_index(self, pkg_dict):
        return pkg_dict

    def before_dataset_view(self, pkg_dict):
        return pkg_dict

    def read(self, entity):
        return entity

    def create(self, entity):
        return entity

    def edit(self, entity):
        return entity

    def delete(self, entity):
        return entity

    # IResourceController callbacks used by CKAN 2.10 and 2.11.

    def after_resource_create(self, context, resource):
        return resource

    def after_resource_update(self, context, resource):
        try:
            package_id = resource.get("package_id") or resource.get("name")
            package = self._package_show(package_id)
            graph = Helper.get_dataset_graph(package)
            Helper.delete_from_sparql(graph)
            Helper.insert_to_sparql(graph)
        except Exception:
            log.exception("Failed to update CRC resource metadata in SPARQL")
        return resource

    def before_resource_delete(self, context, resource, resources):
        try:
            resource_dict = toolkit.get_action("resource_show")(
                {}, {"id": resource["id"]}
            )
            package_id = resource_dict.get("package_id") or resource_dict.get("name")
            package = self._package_show(package_id)
            Helper.delete_from_sparql(Helper.get_dataset_graph(package))
        except Exception:
            log.exception("Failed to delete CRC resource metadata from SPARQL")
        return resources

    def after_resource_delete(self, context, resources):
        return resources

    def before_resource_create(self, context, resource):
        return resource

    def before_resource_update(self, context, current, resource):
        return resource

    def before_resource_show(self, resource_dict):
        return resource_dict

    # CKAN 2.9/early 2.10 compatibility aliases. CKAN 2.11 calls the explicit
    # dataset/resource methods above.

    def after_create(self, context, data):
        if self._is_resource_dict(data):
            return self.after_resource_create(context, data)
        return self.after_dataset_create(context, data)

    def after_update(self, context, data):
        if self._is_resource_dict(data):
            return self.after_resource_update(context, data)
        return self.after_dataset_update(context, data)

    def after_delete(self, context, data):
        if isinstance(data, list):
            return self.after_resource_delete(context, data)
        return self.after_dataset_delete(context, data)

    def after_search(self, search_results, search_params):
        return self.after_dataset_search(search_results, search_params)

    def after_show(self, context, pkg_dict):
        return self.after_dataset_show(context, pkg_dict)

    def before_search(self, search_params):
        return self.before_dataset_search(search_params)

    def before_index(self, pkg_dict):
        return self.before_dataset_index(pkg_dict)

    def before_view(self, pkg_dict):
        return self.before_dataset_view(pkg_dict)

    def before_create(self, context, resource):
        return self.before_resource_create(context, resource)

    def before_update(self, context, current, resource):
        return self.before_resource_update(context, current, resource)

    def before_delete(self, context, resource, resources):
        return self.before_resource_delete(context, resource, resources)

    def before_show(self, resource_dict):
        return self.before_resource_show(resource_dict)

    @staticmethod
    def _package_show(package_id):
        if not package_id:
            raise ValueError("Resource does not identify its parent dataset")
        return toolkit.get_action("package_show")({}, {"name_or_id": package_id})

    @staticmethod
    def _is_resource_dict(data):
        return isinstance(data, dict) and (
            "package_id" in data or "url_type" in data or "resource_type" in data
        )
