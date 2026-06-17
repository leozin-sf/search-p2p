from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import load_config
from .network import P2PNetwork
from .search import SearchEngine, SearchResult


@dataclass(frozen=True)
class SimulationResult:
    topology: str
    topology_summary: dict[str, object]
    search: SearchResult

    def to_dict(self) -> dict[str, object]:
        return {
            "topology": self.topology,
            "topology_summary": dict(self.topology_summary),
            "search": self.search.to_dict(),
        }


class TopologySimulator:
    def __init__(
        self,
        network: P2PNetwork,
        topology: str = "topology",
        seed: int | None = None,
    ):
        self.network = network
        self.topology = topology
        self.engine = SearchEngine(network, seed=seed)

    @classmethod
    def from_topology_file(
        cls, topology_path: str | Path, seed: int | None = None
    ) -> "TopologySimulator":
        path = Path(topology_path)
        return cls(
            P2PNetwork.from_config(load_config(path)),
            topology=str(path),
            seed=seed,
        )

    def search(
        self,
        node_id: str,
        resource_id: str,
        ttl: int,
        algorithm: str,
    ) -> SimulationResult:
        return SimulationResult(
            topology=self.topology,
            topology_summary=self.network.summary(),
            search=self.engine.search(node_id, resource_id, ttl, algorithm),
        )
