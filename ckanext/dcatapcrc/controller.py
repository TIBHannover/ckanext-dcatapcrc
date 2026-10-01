import io
import json
import logging

import ckan.plugins.toolkit as toolkit
from ckan.model import Package
from ckanext.dcat.processors import RDFSerializer
from flask import render_template, send_file

from ckanext.dcatapcrc.libs.helpers import Helper


log = logging.getLogger(__name__)


class BaseController:
    @staticmethod
    def load_admin_view():
        Helper.abort_if_not_admin()
        return render_template("admin_panel.html")

    @staticmethod
    def export_catalog():
        Helper.abort_if_not_admin()
        dataset_dicts = []
        for dataset in Package.search_by_name(""):
            if dataset.state == "active":
                package = toolkit.get_action("package_show")(
                    {}, {"name_or_id": dataset.name}
                )
                dataset_dicts.append(Helper.set_dataset_uri(package))

        serializer = RDFSerializer(profiles=Helper.get_rdf_profiles())
        rdf_output = serializer.serialize_catalog(
            dataset_dicts=dataset_dicts,
            _format="ttl",
        )
        output = io.BytesIO(rdf_output.encode("utf-8"))

        try:
            return send_file(
                output,
                mimetype="text/turtle",
                download_name="ckan-catalog.ttl",
                as_attachment=True,
            )
        except TypeError:
            # Flask < 2.0, retained for CKAN 2.10 installations using it.
            output.seek(0)
            return send_file(
                output,
                mimetype="text/turtle",
                attachment_filename="ckan-catalog.ttl",
                as_attachment=True,
            )

    @staticmethod
    def push_to_sparql():
        Helper.abort_if_not_admin()
        toolkit.enqueue_job(
            push_catalog_to_sparql,
            kwargs={"catalog_graphs": _active_dataset_graphs()},
        )
        return json.dumps({"_result": True})

    @staticmethod
    def delete_from_sparql():
        Helper.abort_if_not_admin()
        toolkit.enqueue_job(
            delete_catalog_from_sparql,
            kwargs={"catalog_graphs": _active_dataset_graphs()},
        )
        return json.dumps({"_result": True})


def _active_dataset_graphs():
    graphs = []
    for dataset in Package.search_by_name(""):
        if dataset.state == "active":
            package = toolkit.get_action("package_show")(
                {}, {"name_or_id": dataset.name}
            )
            graphs.append(Helper.get_dataset_graph(package))
    return graphs


def push_catalog_to_sparql(catalog_graphs):
    for graph in catalog_graphs:
        try:
            Helper.delete_from_sparql(graph)
            Helper.insert_to_sparql(graph)
        except Exception:
            log.exception("Failed to push catalog graph to SPARQL")


def delete_catalog_from_sparql(catalog_graphs):
    for graph in catalog_graphs:
        try:
            Helper.delete_from_sparql(graph)
        except Exception:
            log.exception("Failed to delete catalog graph from SPARQL")
