from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from p2p_search.benchmark import Query, run_benchmark, write_csv, write_svg_chart
from tests.test_search import chain_network


class BenchmarkTests(unittest.TestCase):
    def test_informed_search_benefits_from_repeated_query(self) -> None:
        summaries = run_benchmark(
            chain_network(),
            "chain",
            [Query("n1", "r3", 2), Query("n1", "r3", 2)],
            algorithms=["flooding", "informed_flooding"],
            runs=1,
        )
        self.assertEqual(summaries[0].average_messages, 4)
        self.assertEqual(summaries[1].average_messages, 2)
        self.assertEqual(summaries[1].success_rate, 1)

    def test_writes_csv_and_svg(self) -> None:
        summaries = run_benchmark(
            chain_network(),
            "chain",
            [Query("n1", "r3", 2)],
            algorithms=["flooding"],
            runs=1,
        )
        with tempfile.TemporaryDirectory() as directory:
            csv_path = write_csv(summaries, Path(directory) / "result.csv")
            svg_path = write_svg_chart(summaries, Path(directory) / "result.svg")
            self.assertIn("average_messages", csv_path.read_text())
            self.assertIn("<svg", svg_path.read_text())

    def test_random_variants_share_seed_with_cold_cache(self) -> None:
        summaries = run_benchmark(
            chain_network(),
            "chain",
            [Query("n1", "r3", 2)],
            algorithms=["random_walk", "informed_random_walk"],
            runs=20,
            seed=2026,
        )
        self.assertEqual(
            summaries[0].average_messages,
            summaries[1].average_messages,
        )
        self.assertEqual(summaries[0].success_rate, summaries[1].success_rate)


if __name__ == "__main__":
    unittest.main()
