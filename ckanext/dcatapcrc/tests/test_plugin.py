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
    context = {"user": "editor"}
    graph = object()
    calls = []
    package_show = Mock(return_value=package)
    monkeypatch.setattr(
        plugin_module.toolkit,
        "get_action",
        lambda action: package_show,
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

    result = plugin_module.DcatapcrcPlugin().after_dataset_update(context, package)

    assert result is package
    package_show.assert_called_once_with(context, {"id": "dataset-id"})
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
    context = {"user": "editor"}
    graph = object()
    calls = []
    package_show = Mock(return_value={"id": "dataset-id"})
    monkeypatch.setattr(
        plugin_module.toolkit,
        "get_action",
        lambda action: package_show,
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
        context, {"id": "resource-id", "package_id": "dataset-id"}
    )

    package_show.assert_called_once_with(context, {"id": "dataset-id"})
    assert calls == [("delete", graph), ("insert", graph)]


def test_callback_failure_is_logged_and_does_not_break_ckan(monkeypatch, caplog):
    monkeypatch.setattr(
        plugin_module.DcatapcrcPlugin,
        "_package_show",
        staticmethod(
            lambda context, package_id: (_ for _ in ()).throw(
                RuntimeError("offline")
            )
        ),
    )
    pkg_dict = {"id": "dataset-id"}

    result = plugin_module.DcatapcrcPlugin().after_dataset_create({}, pkg_dict)

    assert result is pkg_dict
    assert "Failed to insert CRC dataset metadata into SPARQL" in caplog.text


def test_package_show_uses_ckan_211_id_and_preserves_context(monkeypatch):
    context = {"user": "editor", "auth_user_obj": object()}
    package_show = Mock(return_value={"id": "dataset-id"})
    monkeypatch.setattr(
        plugin_module.toolkit,
        "get_action",
        lambda action: package_show,
    )

    package = plugin_module.DcatapcrcPlugin._package_show(context, "dataset-id")

    assert package == {"id": "dataset-id"}
    package_show.assert_called_once_with(context, {"id": "dataset-id"})


def test_production_package_show_calls_do_not_use_name_or_id():
    package_root = Path(__file__).parents[1]
    source_files = [package_root / "controller.py", package_root / "plugin.py"]
    source_files.extend((package_root / "libs").rglob("*.py"))

    offenders = [
        str(path.relative_to(package_root))
        for path in source_files
        if "name_or_id" in path.read_text()
    ]

    assert offenders == []


def test_dataset_create_uses_ckan_211_package_show_without_breaking_ckan(
    monkeypatch,
):
    context = {"user": "editor"}
    package = {"id": "dataset-id"}
    package_show = Mock(return_value=package)
    monkeypatch.setattr(
        plugin_module.toolkit,
        "get_action",
        lambda action: package_show,
    )
    monkeypatch.setattr(plugin_module.Helper, "get_dataset_graph", Mock(return_value=[]))
    insert = Mock()
    monkeypatch.setattr(plugin_module.Helper, "insert_to_sparql", insert)

    result = plugin_module.DcatapcrcPlugin().after_dataset_create(context, package)

    assert result is package
    package_show.assert_called_once_with(context, {"id": "dataset-id"})
    insert.assert_called_once_with([])


def test_resource_create_preserves_existing_noop_workflow():
    resource = {"id": "resource-id", "package_id": "dataset-id"}

    result = plugin_module.DcatapcrcPlugin().after_resource_create({}, resource)

    assert result is resource


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


@pytest.mark.parametrize(
    ("method_name", "operation"),
    [
        ("insert_to_sparql", "INSERT"),
        ("delete_from_sparql", "DELETE"),
    ],
)
def test_sparql_updates_use_post_and_execute_each_triple(
    monkeypatch, method_name, operation
):
    endpoint = "https://jena.example.test/dataset/update"
    monkeypatch.setattr(
        helpers.Helper,
        "get_apache_jena_endpoint",
        staticmethod(lambda: endpoint),
    )
    wrapper = Mock()
    wrapper.query.return_value = "response"
    wrapper_factory = Mock(return_value=wrapper)
    monkeypatch.setattr(helpers, "SPARQLWrapper", wrapper_factory)

    result = getattr(helpers.Helper, method_name)(_graph_for_sparql_write())

    assert result == "response"
    wrapper_factory.assert_called_once_with(endpoint)
    wrapper.setMethod.assert_called_once_with(helpers.POST)
    assert wrapper.setQuery.call_count == 1
    assert operation in wrapper.setQuery.call_args.args[0]
    wrapper.query.assert_called_once_with()


@pytest.mark.parametrize(
    ("method_name", "operation"),
    [
        ("insert_to_sparql", "INSERT"),
        ("delete_from_sparql", "DELETE"),
    ],
)
def test_sparql_http_403_is_reported_without_endpoint_or_query(
    monkeypatch, method_name, operation
):
    endpoint = "https://user:secret@jena.example.test/dataset/update"
    monkeypatch.setattr(
        helpers.Helper,
        "get_apache_jena_endpoint",
        staticmethod(lambda: endpoint),
    )
    forbidden = RuntimeError("response body contains sensitive metadata")
    forbidden.code = 403
    wrapper = Mock()
    wrapper.query.side_effect = forbidden
    monkeypatch.setattr(helpers, "SPARQLWrapper", Mock(return_value=wrapper))

    with pytest.raises(helpers.SparqlUpdateError) as error:
        getattr(helpers.Helper, method_name)(_graph_for_sparql_write())

    message = str(error.value)
    assert message == (
        "SPARQL %s failed with HTTP 403 after 0 successful request(s)" % operation
    )
    assert endpoint not in message
    assert "secret" not in message
    assert "sensitive metadata" not in message


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
