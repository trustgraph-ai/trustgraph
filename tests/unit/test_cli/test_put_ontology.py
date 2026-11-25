"""
Unit tests for tg-put-ontology, including fetching ontologies from the
ohi.dev catalog. The catalog client and the config API are mocked.
"""

import hashlib
import pytest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ohi import Format
from rdflib import Graph, URIRef, RDF, OWL

from trustgraph.cli.put_ontology import (
    fetch_from_ohi, put_ontology, main as put_main,
)


PERSON_TTL = b"""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/people#> .
ex:Person a owl:Class .
"""

PERSON_RDFXML = b"""<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:owl="http://www.w3.org/2002/07/owl#">
  <owl:Class rdf:about="http://example.org/people#Person"/>
</rdf:RDF>
"""

AGENT_TTL = b"""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/agents#> .
ex:Agent a owl:Class .
"""

PERSON = URIRef("http://example.org/people#Person")
AGENT = URIRef("http://example.org/agents#Agent")


def artifact(fmt, data, url=None):
    return SimpleNamespace(
        format=fmt,
        url=url or f"https://files.example/{fmt.value}",
        sha256=hashlib.sha256(data).hexdigest(),
    )


def publication(name, artifacts, dependencies=()):
    return SimpleNamespace(
        namespace="example",
        name=name,
        version="1",
        base_url=f"https://files.example/{name}/1/",
        artifacts=artifacts,
        dependencies=[SimpleNamespace(base_url=d) for d in dependencies],
    )


def mock_catalog(publications, files):
    """Catalog client returning publications by reference and files by URL."""
    client = Mock()
    client.inspect.side_effect = lambda ref: publications[ref]
    client.get.side_effect = lambda url: files[url]
    return client


def parse(turtle):
    g = Graph()
    g.parse(data=turtle, format="turtle")
    return g


class TestFetchFromOhi:

    @patch('trustgraph.cli.put_ontology.CatalogClient')
    def test_prefers_owl_turtle(self, mock_client_class, capsys):
        pub = publication("people", [
            artifact(Format.linkml_yaml, b"id: people"),
            artifact(Format.owl_rdfxml, PERSON_RDFXML),
            artifact(Format.owl_turtle, PERSON_TTL),
        ])
        client = mock_catalog(
            {"example/people@1": pub},
            {a.url: d for a, d in zip(
                pub.artifacts, [b"id: people", PERSON_RDFXML, PERSON_TTL]
            )},
        )
        mock_client_class.return_value = client

        g = parse(fetch_from_ohi("example/people@1"))

        assert (PERSON, RDF.type, OWL.Class) in g
        client.get.assert_called_once_with(
            "https://files.example/owl-turtle"
        )
        assert "Fetched example/people@1 from ohi.dev" in capsys.readouterr().out

    @patch('trustgraph.cli.put_ontology.CatalogClient')
    def test_falls_back_to_owl_rdfxml(self, mock_client_class):
        pub = publication("people", [
            artifact(Format.owl_rdfxml, PERSON_RDFXML),
        ])
        mock_client_class.return_value = mock_catalog(
            {"example/people": pub},
            {"https://files.example/owl-rdfxml": PERSON_RDFXML},
        )

        g = parse(fetch_from_ohi("example/people"))

        assert (PERSON, RDF.type, OWL.Class) in g

    @patch('trustgraph.cli.put_ontology.CatalogClient')
    def test_checksum_mismatch(self, mock_client_class):
        pub = publication("people", [artifact(Format.owl_turtle, PERSON_TTL)])
        mock_client_class.return_value = mock_catalog(
            {"example/people": pub},
            {"https://files.example/owl-turtle": PERSON_TTL + b"\n# changed"},
        )

        with pytest.raises(ValueError, match="Checksum mismatch"):
            fetch_from_ohi("example/people")

    @patch('trustgraph.cli.put_ontology.CatalogClient')
    def test_no_owl_artifact(self, mock_client_class):
        pub = publication("people", [
            artifact(Format.linkml_yaml, b"id: people"),
        ])
        mock_client_class.return_value = mock_catalog(
            {"example/people": pub}, {},
        )

        with pytest.raises(ValueError, match="No OWL Turtle or RDF/XML"):
            fetch_from_ohi("example/people")

    @patch('trustgraph.cli.put_ontology.CatalogClient')
    def test_dependencies_not_fetched_by_default(self, mock_client_class):
        agents = publication("agents", [
            artifact(Format.owl_turtle, AGENT_TTL, "https://files.example/a"),
        ])
        people = publication(
            "people",
            [artifact(Format.owl_turtle, PERSON_TTL, "https://files.example/p")],
            dependencies=[agents.base_url],
        )
        client = mock_catalog(
            {"example/people": people, agents.base_url: agents},
            {
                "https://files.example/p": PERSON_TTL,
                "https://files.example/a": AGENT_TTL,
            },
        )
        mock_client_class.return_value = client

        g = parse(fetch_from_ohi("example/people"))

        assert (PERSON, RDF.type, OWL.Class) in g
        assert (AGENT, RDF.type, OWL.Class) not in g
        client.inspect.assert_called_once_with("example/people")

    @patch('trustgraph.cli.put_ontology.CatalogClient')
    def test_include_dependencies_merges_graphs(self, mock_client_class,
                                                capsys):
        agents = publication("agents", [
            artifact(Format.owl_turtle, AGENT_TTL, "https://files.example/a"),
        ])
        people = publication(
            "people",
            [artifact(Format.owl_turtle, PERSON_TTL, "https://files.example/p")],
            dependencies=[agents.base_url],
        )
        mock_client_class.return_value = mock_catalog(
            {"example/people": people, agents.base_url: agents},
            {
                "https://files.example/p": PERSON_TTL,
                "https://files.example/a": AGENT_TTL,
            },
        )

        g = parse(fetch_from_ohi("example/people", include_dependencies=True))

        assert (PERSON, RDF.type, OWL.Class) in g
        assert (AGENT, RDF.type, OWL.Class) in g
        out = capsys.readouterr().out
        assert "Fetched example/people@1" in out
        assert "Fetched example/agents@1" in out


class TestPutOntology:

    @patch('trustgraph.cli.put_ontology.Api')
    def test_stores_jsonld_config_value(self, mock_api_class):
        mock_config = Mock()
        mock_api_class.return_value.config.return_value = mock_config

        put_ontology(
            "http://test.com", "people", PERSON_TTL.decode(), "turtle",
        )

        config_value = mock_config.put.call_args[0][0][0]
        assert config_value.type == "ontology"
        assert config_value.key == "people"
        g = Graph()
        g.parse(data=config_value.value, format="json-ld")
        assert (PERSON, RDF.type, OWL.Class) in g


class TestPutOntologyMain:

    def test_ohi_argument(self):
        test_args = [
            'tg-put-ontology',
            '--ohi', 'w3c/prov-o@2013',
            '--ontology-id', 'prov-o',
            '--include-dependencies',
        ]

        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.put_ontology.fetch_from_ohi',
                   return_value="TURTLE") as mock_fetch, \
             patch('trustgraph.cli.put_ontology.put_ontology') as mock_put:

            put_main()

            mock_fetch.assert_called_once_with('w3c/prov-o@2013', True)
            mock_put.assert_called_once_with(
                url='http://localhost:8888/',
                ontology_id='prov-o',
                data="TURTLE",
                fmt="turtle",
                token=None,
                workspace='default',
            )

    @pytest.mark.parametrize("extra_args", [
        ['--ohi', 'w3c/prov-o', 'prov.ttl'],
        ['--ohi', 'w3c/prov-o', '--format', 'turtle'],
        ['--include-dependencies', 'prov.ttl'],
    ])
    def test_invalid_argument_combinations(self, extra_args):
        test_args = ['tg-put-ontology', '-i', 'prov-o'] + extra_args

        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.put_ontology.fetch_from_ohi') as mock_fetch:
            with pytest.raises(SystemExit):
                put_main()

            mock_fetch.assert_not_called()

    def test_ohi_error_is_reported(self, capsys):
        test_args = ['tg-put-ontology', '--ohi', 'nope/nope', '-i', 'x']

        with patch('sys.argv', test_args), \
             patch('trustgraph.cli.put_ontology.fetch_from_ohi',
                   side_effect=Exception("no ontology matches nope/nope")):
            with pytest.raises(SystemExit) as exc:
                put_main()

        assert exc.value.code == 1
        assert "Exception: no ontology matches nope/nope" in \
            capsys.readouterr().out
