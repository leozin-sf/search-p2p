from __future__ import annotations

import unittest

from p2p_search.config import ConfigError, parse_config


def valid_data() -> dict[str, object]:
    return {
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


class ConfigTests(unittest.TestCase):
    def test_valid_configuration(self) -> None:
        config = parse_config(valid_data())
        self.assertEqual(config.num_nodes, 3)
        self.assertEqual(config.node_ids, ("n1", "n2", "n3"))
        self.assertEqual(len(config.edges), 2)

    def test_accepts_comma_separated_resources(self) -> None:
        data = valid_data()
        data["resources"]["n1"] = "r1, shared"  # type: ignore[index]
        config = parse_config(data)
        self.assertEqual(config.resources["n1"], frozenset({"r1", "shared"}))

    def test_rejects_partitioned_network(self) -> None:
        data = valid_data()
        data["min_neighbors"] = 0
        data["edges"] = [["n1", "n2"]]
        with self.assertRaisesRegex(ConfigError, "particionada"):
            parse_config(data)

    def test_rejects_degree_outside_limits(self) -> None:
        data = valid_data()
        data["min_neighbors"] = 2
        with self.assertRaisesRegex(ConfigError, "possui 1 vizinho"):
            parse_config(data)

    def test_rejects_node_without_resources(self) -> None:
        data = valid_data()
        data["resources"]["n2"] = []  # type: ignore[index]
        with self.assertRaisesRegex(ConfigError, "nao possui recursos"):
            parse_config(data)

    def test_rejects_self_loop(self) -> None:
        data = valid_data()
        data["edges"].append(["n1", "n1"])  # type: ignore[union-attr]
        with self.assertRaisesRegex(ConfigError, "laco nao permitido"):
            parse_config(data)

    def test_rejects_unknown_node_in_edge(self) -> None:
        data = valid_data()
        data["edges"].append(["n3", "n4"])  # type: ignore[union-attr]
        with self.assertRaisesRegex(ConfigError, "inexistente"):
            parse_config(data)

    def test_rejects_duplicate_edge(self) -> None:
        data = valid_data()
        data["edges"].append(["n2", "n1"])  # type: ignore[union-attr]
        with self.assertRaisesRegex(ConfigError, "duplicada"):
            parse_config(data)

    def test_rejects_node_count_mismatch(self) -> None:
        data = valid_data()
        data["num_nodes"] = 4
        with self.assertRaisesRegex(ConfigError, "resources define 3"):
            parse_config(data)


if __name__ == "__main__":
    unittest.main()

