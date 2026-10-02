import logging
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml
import ckan.plugins as plugins
from ckan.common import CKANConfig
from ckan.config.declaration import Declaration, Key
from rdflib import BNode, Graph, Literal, URIRef

from ckanext.dcatapcrc import controller
from ckanext.dcatapcrc import plugin as plugin_module
from ckanext.dcatapcrc.libs import helpers
from ckanext.dcatapcrc.profiles.crc_profile import CRCDCATAPProfile


CANONICAL_JENA_KEY = "ckanext.dcatapcrc.apachejena.endpoint"
HISTORICAL_JENA_KEY = "ckanext.apacheJena.endpoint"


def _declared_config(values):
    declaration = Declaration()
    plugin_module.DcatapcrcPlugin().declare_config_options(declaration, Key())
    config = CKANConfig(values)
    declaration.make_safe(config)
    return declaration, config


@pytest.mark.ckan_config("ckan.plugins", "dcat_crc")
@pytest.mark.usefixtures("with_plugins")
def test_canonical_jena_endpoint_is_declared(ckan_config, caplog):
    assert ckan_config.is_declared(CANONICAL_JENA_KEY)
    ckan_config.get(CANONICAL_JENA_KEY)
    assert f"Option {CANONICAL_JENA_KEY} is not declared" not in caplog.text


def test_plugin_declares_only_dcatapcrc_owned_config():
    assert plugins.IConfigDeclaration.implemented_by(plugin_module.DcatapcrcPlugin)
    declaration = Declaration()
    plugin_module.DcatapcrcPlugin().declare_config_options(declaration, Key())

    assert declaration.get(CANONICAL_JENA_KEY).legacy_key == HISTORICAL_JENA_KEY
    assert "ckanext.apachejena.endpoint" not in declaration


def test_canonical_jena_endpoint_is_used(monkeypatch):
    declaration, config = _declared_config(
        {CANONICAL_JENA_KEY: "https://jena.example.test/canonical"}
    )
    monkeypatch.setattr(helpers.toolkit, "config", config)

    assert declaration.get(CANONICAL_JENA_KEY).legacy_key == HISTORICAL_JENA_KEY
    assert helpers.Helper.get_apache_jena_endpoint() == (
        "https://jena.example.test/canonical"
    )


def test_historical_jena_endpoint_remains_supported(monkeypatch, caplog):
    _, config = _declared_config(
        {HISTORICAL_JENA_KEY: "https://jena.example.test/historical"}
    )
    monkeypatch.setattr(helpers.toolkit, "config", config)

    assert helpers.Helper.get_apache_jena_endpoint() == (
        "https://jena.example.test/historical"
    )
    assert HISTORICAL_JENA_KEY in caplog.text


def test_canonical_jena_endpoint_takes_precedence_over_historical(monkeypatch):
    _, config = _declared_config(
        {
            CANONICAL_JENA_KEY: "https://jena.example.test/canonical",
            HISTORICAL_JENA_KEY: "https://jena.example.test/historical",
        }
    )
    monkeypatch.setattr(helpers.toolkit, "config", config)

    assert helpers.Helper.get_apache_jena_endpoint() == (
        "https://jena.example.test/canonical"
    )


def test_check_plugin_enabled_with_string_config(monkeypatch):
    monkeypatch.setitem(
        helpers.toolkit.config,
        "ckan.plugins",
        "stats dcat_crc dataset_reference",
    )

    assert helpers.check_plugin_enabled("dcat_crc")
    assert not helpers.check_plugin_enabled("machine_link")


def test_check_plugin_enabled_with_iterable_config(monkeypatch):
    monkeypatch.setitem(
        helpers.toolkit.config,
        "ckan.plugins",
        ["stats", "dcat_crc", "dataset_reference"],
    )

    assert helpers.check_plugin_enabled("dcat_crc")
    assert not helpers.check_plugin_enabled("machine_link")

    monkeypatch.setitem(
        helpers.toolkit.config,
        "ckan.plugins",
        ("stats", "machine_link"),
    )

    assert helpers.check_plugin_enabled("machine_link")
    assert not helpers.check_plugin_enabled("dcat_crc")


def test_check_plugin_enabled_with_missing_none_or_empty_config(monkeypatch):
    monkeypatch.delitem(helpers.toolkit.config, "ckan.plugins", raising=False)
    assert not helpers.check_plugin_enabled("dcat_crc")

    for value in (None, "", []):
        monkeypatch.setitem(helpers.toolkit.config, "ckan.plugins", value)
        assert not helpers.check_plugin_enabled("dcat_crc")


def test_update_config_registers_assets_and_default_profiles(monkeypatch):
    registered = []
    monkeypatch.setattr(
        plugin_module.toolkit,
        "add_template_directory",
        lambda config, path: registered.append(("templates", path)),
    )
    monkeypatch.setattr(
        plugin_module.toolkit,
        "add_public_directory",
        lambda config, path: registered.append(("public", path)),
    )
    monkeypatch.setattr(
        plugin_module.toolkit,
        "add_resource",
        lambda path, name: registered.append(("resource", path, name)),
    )
    config = {}

    plugin_module.DcatapcrcPlugin().update_config(config)

    assert config["ckanext.dcat.rdf.profiles"] == "euro_dcat_ap_2 crc_dcat_ap"
    assert registered == [
        ("templates", "templates"),
        ("public", "public"),
        ("resource", "public/statics", "ckanext-dcatapcrc"),
    ]


def test_plugin_exposes_ckan_210_and_211_callback_names():
    plugin = plugin_module.DcatapcrcPlugin()

    assert hasattr(plugin, "after_dataset_create")
    assert hasattr(plugin, "after_dataset_update")
    assert hasattr(plugin, "after_dataset_delete")
    assert hasattr(plugin, "after_resource_update")
    assert hasattr(plugin, "before_resource_delete")


def test_dataset_update_replaces_existing_sparql_graph(monkeypatch):
    package = {"id": "dataset-id"}
    graph = object()
    calls = []
    monkeypatch.setattr(
        plugin_module.DcatapcrcPlugin,
        "_package_show",
        staticmethod(lambda package_id: package),
    )
    monkeypatch.setattr(plugin_module.Helper, "get_dataset_graph", lambda value: graph)
    monkeypatch.setattr(
        plugin_module.Helper,
        "delete_from_sparql",
        lambda value: calls.append(("delete", value)),
    )
    monkeypatch.setattr(
        plugin_module.Helper,
        "insert_to_sparql",
        lambda value: calls.append(("insert", value)),
    )

    result = plugin_module.DcatapcrcPlugin().after_dataset_update(
        {}, {"id": "dataset-id"}
    )

    assert result == {"id": "dataset-id"}
    assert calls == [("delete", graph), ("insert", graph)]


def test_legacy_after_update_dispatches_dataset_and_resource(monkeypatch):
    plugin = plugin_module.DcatapcrcPlugin()
    calls = []
    monkeypatch.setattr(
        plugin,
        "after_dataset_update",
        lambda context, data: calls.append("dataset") or data,
    )
    monkeypatch.setattr(
        plugin,
        "after_resource_update",
        lambda context, data: calls.append("resource") or data,
    )

    plugin.after_update({}, {"id": "dataset-id"})
    plugin.after_update({}, {"id": "resource-id", "package_id": "dataset-id"})

    assert calls == ["dataset", "resource"]


def test_resource_update_replaces_parent_dataset_graph(monkeypatch):
    graph = object()
    calls = []
    monkeypatch.setattr(
        plugin_module.DcatapcrcPlugin,
        "_package_show",
        staticmethod(lambda package_id: {"id": package_id}),
    )
    monkeypatch.setattr(plugin_module.Helper, "get_dataset_graph", lambda value: graph)
    monkeypatch.setattr(
        plugin_module.Helper,
        "delete_from_sparql",
        lambda value: calls.append(("delete", value)),
    )
    monkeypatch.setattr(
        plugin_module.Helper,
        "insert_to_sparql",
        lambda value: calls.append(("insert", value)),
    )

    plugin_module.DcatapcrcPlugin().after_resource_update(
        {}, {"id": "resource-id", "package_id": "dataset-id"}
    )

    assert calls == [("delete", graph), ("insert", graph)]


def test_callback_failure_is_logged_and_does_not_break_ckan(monkeypatch, caplog):
    monkeypatch.setattr(
        plugin_module.DcatapcrcPlugin,
        "_package_show",
        staticmethod(lambda package_id: (_ for _ in ()).throw(RuntimeError("offline"))),
    )
    pkg_dict = {"id": "dataset-id"}

    result = plugin_module.DcatapcrcPlugin().after_dataset_create({}, pkg_dict)

    assert result is pkg_dict
    assert "Failed to insert CRC dataset metadata into SPARQL" in caplog.text


def test_rdf_profiles_keep_crc_profile(monkeypatch):
    monkeypatch.setitem(
        helpers.toolkit.config,
        "ckanext.dcat.rdf.profiles",
        "euro_dcat_ap_2",
    )

    assert helpers.Helper.get_rdf_profiles() == ["euro_dcat_ap_2", "crc_dcat_ap"]
    assert helpers.Helper.get_rdf_profiles(
        {"profiles": ["euro_dcat_ap_2", "crc_dcat_ap"]}
    ) == ["euro_dcat_ap_2", "crc_dcat_ap"]


def test_dataset_and_resource_uris_include_root_path(monkeypatch):
    monkeypatch.setitem(helpers.toolkit.config, "ckan.site_url", "https://data.test/")
    monkeypatch.setitem(helpers.toolkit.config, "ckan.root_path", "/en/{{LANG}}")
    package = {
        "id": "dataset-id",
        "name": "dataset-name",
        "resources": [{"id": "resource-id"}],
    }

    result = helpers.Helper.set_dataset_uri(package)

    assert result["uri"] == "https://data.test/en/dataset/dataset-id"
    assert result["resources"][0]["uri"] == (
        "https://data.test/en/dataset/dataset-name/resource/resource-id"
    )


def test_sparql_terms_use_rdflib_serialization():
    subject, predicate, obj = helpers.Helper.clean_triples(
        BNode("N1"),
        URIRef("https://schema.org/citation"),
        Literal("O'Brien"),
    )

    assert subject == "_:N1"
    assert predicate == "<https://schema.org/citation>"
    assert obj == '"O\'Brien"'


def _graph_for_sparql_write():
    graph = Graph()
    graph.add(
        (
            URIRef("https://data.test/dataset/one"),
            URIRef("https://schema.org/name"),
            Literal("Dataset"),
        )
    )
    return graph


def test_missing_jena_endpoint_skips_insert(monkeypatch, caplog):
    _, config = _declared_config({})
    monkeypatch.setattr(helpers.toolkit, "config", config)
    sparql_wrapper = Mock()
    monkeypatch.setattr(helpers, "SPARQLWrapper", sparql_wrapper)

    assert helpers.Helper.insert_to_sparql(_graph_for_sparql_write()) is None
    sparql_wrapper.assert_not_called()
    assert "No Apache Jena endpoint configured; skipping SPARQL insert" in caplog.text


def test_missing_jena_endpoint_skips_delete(monkeypatch, caplog):
    _, config = _declared_config({})
    monkeypatch.setattr(helpers.toolkit, "config", config)
    sparql_wrapper = Mock()
    monkeypatch.setattr(helpers, "SPARQLWrapper", sparql_wrapper)

    assert helpers.Helper.delete_from_sparql(_graph_for_sparql_write()) is None
    sparql_wrapper.assert_not_called()
    assert "No Apache Jena endpoint configured; skipping SPARQL delete" in caplog.text


def test_export_catalog_supports_empty_catalog(monkeypatch):
    captured = {}

    class Serializer:
        def __init__(self, profiles):
            captured["profiles"] = profiles

        def serialize_catalog(self, dataset_dicts, _format):
            captured["datasets"] = dataset_dicts
            captured["format"] = _format
            return "catalog"

    monkeypatch.setattr(controller.Helper, "abort_if_not_admin", lambda: None)
    monkeypatch.setattr(controller.Helper, "get_rdf_profiles", lambda: ["crc_dcat_ap"])
    monkeypatch.setattr(controller.Package, "search_by_name", lambda value: [])
    monkeypatch.setattr(controller, "RDFSerializer", Serializer)
    monkeypatch.setattr(
        controller,
        "send_file",
        lambda output, **kwargs: (output.read(), kwargs),
    )

    content, options = controller.BaseController.export_catalog()

    assert content == b"catalog"
    assert captured == {
        "profiles": ["crc_dcat_ap"],
        "datasets": [],
        "format": "ttl",
    }
    assert options["download_name"] == "ckan-catalog.ttl"
    assert options["mimetype"] == "text/turtle"


def test_export_catalog_falls_back_to_old_flask_filename(monkeypatch):
    calls = []

    class Serializer:
        def __init__(self, profiles):
            pass

        def serialize_catalog(self, dataset_dicts, _format):
            return "catalog"

    def old_send_file(output, **kwargs):
        calls.append(kwargs)
        if "download_name" in kwargs:
            raise TypeError("unexpected keyword")
        return output.read(), kwargs

    monkeypatch.setattr(controller.Helper, "abort_if_not_admin", lambda: None)
    monkeypatch.setattr(controller.Helper, "get_rdf_profiles", lambda: ["crc_dcat_ap"])
    monkeypatch.setattr(controller.Package, "search_by_name", lambda value: [])
    monkeypatch.setattr(controller, "RDFSerializer", Serializer)
    monkeypatch.setattr(controller, "send_file", old_send_file)

    content, options = controller.BaseController.export_catalog()

    assert content == b"catalog"
    assert options["attachment_filename"] == "ckan-catalog.ttl"
    assert len(calls) == 2


def test_crc_profile_preserves_custom_dataset_and_resource_triples(monkeypatch):
    graph = Graph()
    profile = CRCDCATAPProfile(graph)
    dataset_ref = URIRef("https://data.test/dataset/one")
    monkeypatch.setattr(
        "ckanext.dcatapcrc.profiles.crc_profile.Helper.get_linked_publication",
        lambda name: ["Publication citation"],
    )
    monkeypatch.setattr(
        "ckanext.dcatapcrc.profiles.crc_profile.Helper.get_linked_machines",
        lambda resource_id: {"Machine": "https://example.test/machine"},
    )
    monkeypatch.setattr(
        "ckanext.dcatapcrc.profiles.crc_profile.Helper.get_linked_samples",
        lambda resource_id: {"Sample": "https://example.test/sample"},
    )
    dataset = {
        "name": "one",
        "resources": [
            {
                "id": "resource-id",
                "uri": "https://data.test/dataset/one/resource/resource-id",
                "material_combination": "alloy",
                "surface_preparation": "polished",
                "atmosphere": "argon",
                "data_type": "measurement",
                "analysis_method": "microscopy",
            }
        ],
    }

    profile.graph_from_dataset(dataset, dataset_ref)

    assert (
        dataset_ref,
        URIRef("https://schema.org/citation"),
        Literal("Publication citation"),
    ) in graph
    distribution = URIRef(dataset["resources"][0]["uri"])
    assert (
        distribution,
        URIRef("http://emmo.info/emmo/Material"),
        Literal("alloy"),
    ) in graph
    assert (
        distribution,
        URIRef("http://purl.obolibrary.org/obo/ncit/AnalysisMethod"),
        Literal("microscopy"),
    ) in graph


def test_webassets_have_local_contents_and_no_removed_jquery_ui():
    asset_root = Path(__file__).parents[1] / "public" / "statics"
    bundles = yaml.safe_load((asset_root / "webassets.yml").read_text())

    for bundle in bundles.values():
        assert "vendor/jquery.ui.core" not in bundle["extra"]["preload"]
        assert all((asset_root / filename).is_file() for filename in bundle["contents"])
