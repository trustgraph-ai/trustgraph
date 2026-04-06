from trustgraph.messaging.translators.retrieval import GraphRagRequestTranslator


class TestGraphRagRequestTranslator:
    def test_accepts_hyphenated_keys(self):
        translator = GraphRagRequestTranslator()

        result = translator.to_pulsar(
            {
                "query": "q",
                "user": "u",
                "collection": "c",
                "entity-limit": 8,
                "triple-limit": 16,
                "max-subgraph-size": 24,
                "max-path-length": 2,
                "edge-score-limit": 12,
                "edge-limit": 6,
            }
        )

        assert result.entity_limit == 8
        assert result.triple_limit == 16
        assert result.max_subgraph_size == 24
        assert result.max_path_length == 2
        assert result.edge_score_limit == 12
        assert result.edge_limit == 6

    def test_accepts_snake_case_aliases_and_uses_aligned_default(self):
        translator = GraphRagRequestTranslator()

        result = translator.to_pulsar(
            {
                "query": "q",
                "user": "u",
                "collection": "c",
                "entity_limit": 5,
                "triple_limit": 7,
                "max_subgraph_size": 9,
                "max_path_length": 1,
                "edge_score_limit": 11,
                "edge_limit": 3,
            }
        )

        assert result.entity_limit == 5
        assert result.triple_limit == 7
        assert result.max_subgraph_size == 9
        assert result.max_path_length == 1
        assert result.edge_score_limit == 11
        assert result.edge_limit == 3

        defaulted = translator.to_pulsar({"query": "q"})
        assert defaulted.max_subgraph_size == 150
