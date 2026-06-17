from __future__ import annotations

import unittest

from p2p_search.config import parse_config
from p2p_search.network import P2PNetwork
from p2p_search.search import SearchEngine


def chain_network() -> P2PNetwork:
    config = parse_config(
        {
            "num_nodes": 3,
            "min_neighbors": 1,
            "max_neighbors": 2,
            "resources": {
                "n1": ["r1"],
                "n2": ["r2"],
                "n3": ["r3"],
            },
            "edges": [["n1", "n2"], ["n2", "n3"]],
        }
    )
    return P2PNetwork(config)


class SearchTests(unittest.TestCase):
    def test_flooding_finds_resource_and_counts_reply(self) -> None:
        result = SearchEngine(chain_network()).search("n1", "r3", 2, "flooding")
        self.assertTrue(result.found)
        self.assertEqual(result.owner, "n3")
        self.assertEqual(result.query_messages, 2)
        self.assertEqual(result.response_messages, 2)
        self.assertEqual(result.total_messages, 4)
        self.assertEqual(result.nodes_involved, 3)
        self.assertEqual(result.path, ("n1", "n2", "n3"))

    def test_flooding_stops_at_ttl(self) -> None:
        result = SearchEngine(chain_network()).search("n1", "r3", 1, "flooding")
        self.assertFalse(result.found)
        self.assertEqual(result.reason, "ttl_exhausted")
        self.assertEqual(result.total_messages, 1)
        self.assertEqual(result.nodes_involved, 2)

    def test_flooding_counts_duplicate_messages_in_cycles(self) -> None:
        network = P2PNetwork(
            parse_config(
                {
                    "num_nodes": 3,
                    "min_neighbors": 2,
                    "max_neighbors": 2,
                    "resources": {
                        "n1": ["r1"],
                        "n2": ["r2"],
                        "n3": ["r3"],
                    },
                    "edges": [
                        ["n1", "n2"],
                        ["n2", "n3"],
                        ["n3", "n1"],
                    ],
                }
            )
        )
        result = SearchEngine(network).search("n1", "missing", 2, "flooding")
        self.assertFalse(result.found)
        self.assertEqual(result.query_messages, 4)
        self.assertEqual(result.nodes_involved, 3)

    def test_local_resource_uses_no_messages(self) -> None:
        result = SearchEngine(chain_network()).search("n1", "r1", 0, "flooding")
        self.assertTrue(result.found)
        self.assertEqual(result.total_messages, 0)
        self.assertEqual(result.nodes_involved, 1)

    def test_absent_resource_is_reported(self) -> None:
        result = SearchEngine(chain_network()).search("n1", "missing", 2, "flooding")
        self.assertFalse(result.found)
        self.assertEqual(result.reason, "resource_absent")

    def test_random_walk_uses_one_query_per_hop(self) -> None:
        result = SearchEngine(chain_network(), seed=0).search(
            "n1", "r3", 2, "random_walk"
        )
        self.assertTrue(result.found)
        self.assertEqual(result.path, ("n1", "n2", "n3"))
        self.assertEqual(result.query_messages, 2)
        self.assertEqual(result.response_messages, 2)
        self.assertEqual(result.total_messages, 4)

    def test_random_walk_can_revisit_nodes(self) -> None:
        result = SearchEngine(chain_network(), seed=1).search(
            "n1", "r3", 2, "random_walk"
        )
        self.assertFalse(result.found)
        self.assertEqual(result.path, ("n1", "n2", "n1"))
        self.assertEqual(result.nodes_involved, 2)

    def test_success_populates_cache_for_informed_search(self) -> None:
        network = chain_network()
        engine = SearchEngine(network)
        first = engine.search("n1", "r3", 2, "flooding")
        second = engine.search("n1", "r3", 2, "informed_flooding")
        self.assertEqual(first.total_messages, 4)
        self.assertTrue(second.found)
        self.assertEqual(second.found_via, "cache")
        self.assertEqual(second.owner, "n3")
        self.assertEqual(second.total_messages, 0)

    def test_intermediate_cache_answers_informed_search(self) -> None:
        network = chain_network()
        engine = SearchEngine(network)
        engine.search("n1", "r3", 2, "flooding")
        network.nodes["n1"].cache.clear()
        result = engine.search("n1", "r3", 2, "informed_flooding")
        self.assertEqual(result.responder, "n2")
        self.assertEqual(result.found_via, "cache")
        self.assertEqual(result.total_messages, 2)

    def test_uninformed_search_ignores_cache(self) -> None:
        network = chain_network()
        engine = SearchEngine(network)
        engine.search("n1", "r3", 2, "flooding")
        result = engine.search("n1", "r3", 2, "flooding")
        self.assertEqual(result.total_messages, 4)
        self.assertEqual(result.found_via, "resource")

    def test_invalid_algorithm_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Algoritmo invalido"):
            SearchEngine(chain_network()).search("n1", "r3", 2, "invalid")

    def test_invalid_origin_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "inexistente"):
            SearchEngine(chain_network()).search("n9", "r3", 2, "flooding")

    def test_negative_ttl_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "ttl"):
            SearchEngine(chain_network()).search("n1", "r3", -1, "flooding")


if __name__ == "__main__":
    unittest.main()
