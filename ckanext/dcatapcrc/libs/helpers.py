import logging

import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as toolkit
from ckanext.dcat.processors import RDFSerializer
from SPARQLWrapper import POST, SPARQLWrapper
from sqlalchemy.sql.expression import false


log = logging.getLogger(__name__)

DEFAULT_DCAT_PROFILES = ["euro_dcat_ap_2", "crc_dcat_ap"]


def check_plugin_enabled(plugin_name):
    enabled_plugins = toolkit.config.get("ckan.plugins") or []
    if isinstance(enabled_plugins, str):
        enabled_plugins = enabled_plugins.split()
    return plugin_name in enabled_plugins


class Helper:
    @staticmethod
    def abort_if_not_admin():
        context = {
            "model": model,
            "user": toolkit.g.user,
            "auth_user_obj": toolkit.g.userobj,
        }
        try:
            logic.check_access("sysadmin", context, {})
        except logic.NotAuthorized:
            toolkit.abort(404, "Not Found")

    @staticmethod
    def get_apache_jena_endpoint():
        return toolkit.config.get("ckanext.apacheJena.endpoint")

    @staticmethod
    def get_linked_publication(dataset_name):
        if not check_plugin_enabled("dataset_reference"):
            return None

        package_reference_link = Helper._package_reference_model()
        if package_reference_link is None:
            return None

        linked_publications = []
        result = package_reference_link({}).get_by_package(name=dataset_name)
        if result != false:
            linked_publications.extend(item.citation for item in result)
        return linked_publications

    @staticmethod
    def get_linked_machines(resource_id):
        if not check_plugin_enabled("machine_link"):
            return {}
        mediawiki_helper = Helper._machine_link_helper()
        if mediawiki_helper is None:
            return {}
        return mediawiki_helper.get_machine_link(resource_id)

    @staticmethod
    def get_linked_samples(resource_id):
        if not check_plugin_enabled("sample_link"):
            return {}
        sample_link_helper = Helper._sample_link_helper()
        if sample_link_helper is None:
            return {}
        return sample_link_helper.get_sample_link(resource_id)

    @staticmethod
    def insert_to_sparql(graph):
        endpoint = Helper.get_apache_jena_endpoint()
        if not endpoint:
            log.warning("No Apache Jena endpoint configured; skipping SPARQL insert")
            return None

        results = None
        for subject, predicate, obj in graph:
            subject, predicate, obj = Helper.clean_triples(subject, predicate, obj)
            query = "INSERT DATA{ %s %s %s . }" % (subject, predicate, obj)
            sparql = SPARQLWrapper(endpoint)
            sparql.setMethod(POST)
            sparql.setQuery(query)
            results = sparql.query()
        return results

    @staticmethod
    def delete_from_sparql(graph):
        endpoint = Helper.get_apache_jena_endpoint()
        if not endpoint:
            log.warning("No Apache Jena endpoint configured; skipping SPARQL delete")
            return None

        results = None
        for subject, predicate, obj in graph:
            subject, predicate, obj = Helper.clean_triples(subject, predicate, obj)
            if obj.startswith("_:"):
                query = (
                    "DELETE{ %s %s ?bnode . ?bnode ?p ?o .} "
                    "WHERE{ %s %s ?bnode . ?bnode ?p ?o . "
                    "FILTER (isBlank(?bnode))}"
                ) % (subject, predicate, subject, predicate)
            elif not subject.startswith("_:") and not predicate.startswith("_:"):
                query = "DELETE WHERE{ %s %s ?anything . }" % (subject, predicate)
            else:
                continue

            sparql = SPARQLWrapper(endpoint)
            sparql.setMethod(POST)
            sparql.setQuery(query)
            results = sparql.query()
        return results

    @staticmethod
    def get_dataset_graph(dataset_dict):
        dataset_dict = Helper.set_dataset_uri(dataset_dict)
        serializer = RDFSerializer(profiles=Helper.get_rdf_profiles(dataset_dict))
        serializer.graph_from_dataset(dataset_dict)
        return serializer.g

    @staticmethod
    def clean_triples(subject, predicate, obj):
        return [
            Helper._sparql_term(subject),
            Helper._sparql_term(predicate),
            Helper._sparql_term(obj),
        ]

    @staticmethod
    def set_dataset_uri(package):
        root_path = toolkit.config.get("ckan.root_path")
        site_url = toolkit.config.get("ckan.site_url", "").rstrip("/")
        path_prefix = root_path.split("/{{LANG}}")[0].rstrip("/") if root_path else ""
        package["uri"] = "%s%s/dataset/%s" % (site_url, path_prefix, package["id"])
        for resource in package.get("resources", []):
            resource["uri"] = "%s%s/dataset/%s/resource/%s" % (
                site_url,
                path_prefix,
                package["name"],
                resource["id"],
            )
        return package

    # Preserve the original public helper name used by downstream code.
    setDatasetUri = set_dataset_uri

    @staticmethod
    def get_rdf_profiles(dataset_dict=None):
        profiles = dataset_dict.get("profiles") if dataset_dict else None
        if not profiles:
            profiles = toolkit.config.get("ckanext.dcat.rdf.profiles")

        if isinstance(profiles, str):
            profiles = profiles.split()
        elif profiles:
            profiles = list(profiles)
        else:
            profiles = list(DEFAULT_DCAT_PROFILES)

        if "crc_dcat_ap" not in profiles:
            profiles.append("crc_dcat_ap")
        return profiles

    @staticmethod
    def _sparql_term(term):
        if hasattr(term, "n3"):
            return term.n3()
        value = str(term)
        if value.startswith("N"):
            return "_:" + value
        if value.startswith("http"):
            return "<" + value + ">"
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

    @staticmethod
    def _package_reference_model():
        try:
            from ckanext.dataset_reference.models.package_reference_link import (
                PackageReferenceLink,
            )

            return PackageReferenceLink
        except ImportError:
            log.warning("dataset_reference plugin is enabled but not importable")
            return None

    @staticmethod
    def _machine_link_helper():
        try:
            from ckanext.semantic_media_wiki.libs.media_wiki import Helper as MediaWikiHelper

            return MediaWikiHelper
        except ImportError:
            log.warning("machine_link plugin is enabled but not importable")
            return None

    @staticmethod
    def _sample_link_helper():
        try:
            from ckanext.semantic_media_wiki.libs.sample_link import SampleLinkHelper

            return SampleLinkHelper
        except ImportError:
            log.warning("sample_link plugin is enabled but not importable")
            return None
