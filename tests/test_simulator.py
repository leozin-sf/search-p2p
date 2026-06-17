from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from p2p_search.cli import main
from p2p_search.simulator import TopologySimulator
from tests.test_search import chain_network


class SimulatorTests(unittest.TestCase):
    def test_simulator_runs_search_from_loaded_topology(self) -> None:
        simulator = TopologySimulator(chain_network(), topology="chain")
        result = simulator.search("n1", "r3", 2, "flooding")
        self.assertEqual(result.topology, "chain")
        self.assertEqual(result.topology_summary["nodes"], 3)
        self.assertTrue(result.search.found)
        self.assertEqual(result.search.path, ("n1", "n2", "n3"))
        self.assertEqual(
            result.to_dict()["search"]["path"],
            ["n1", "n2", "n3"],
        )

    def test_simulate_cli_accepts_algorithm_with_spaces(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(
                [
                    "simulate",
                    "examples/ring_12.json",
                    "--node-id",
                    "n1",
                    "--resource-id",
                    "r7",
                    "--ttl",
                    "6",
                    "--algorithm",
                    "informed flooding",
                ]
            )
        text = output.getvalue()
        self.assertEqual(status, 0)
        self.assertIn("Topologia: examples/ring_12.json", text)
        self.assertIn("Resultado: ENCONTRADO", text)
        self.assertIn("Algoritmo: informed_flooding", text)


if __name__ == "__main__":
    unittest.main()
