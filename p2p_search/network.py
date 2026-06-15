from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import NetworkConfig, _natural_key


@dataclass
class Node:
    node_id: str
    resources: frozenset[str]
    cache: dict[str, str] = field(default_factory=dict)


class P2PNetwork:
    def __init__(self, config: NetworkConfig):
        self.config = config
        self.nodes = {
            node_id: Node(node_id, resources)
            for node_id, resources in config.resources.items()
        }
        self.adjacency: dict[str, set[str]] = {
            node_id: set() for node_id in self.nodes
        }
        for left, right in config.edges:
            self.adjacency[left].add(right)
            self.adjacency[right].add(left)

    @classmethod
    def from_config(cls, config: NetworkConfig) -> "P2PNetwork":
        return cls(config)

    def clone(self, include_cache: bool = False) -> "P2PNetwork":
        network = P2PNetwork(self.config)
        if include_cache:
            for node_id, node in self.nodes.items():
                network.nodes[node_id].cache.update(node.cache)
        return network

    def clear_caches(self) -> None:
        for node in self.nodes.values():
            node.cache.clear()

    def neighbors(self, node_id: str) -> tuple[str, ...]:
        return tuple(sorted(self.adjacency[node_id], key=_natural_key))

    def owners(self, resource_id: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                (
                    node_id
                    for node_id, node in self.nodes.items()
                    if resource_id in node.resources
                ),
                key=_natural_key,
            )
        )

    def summary(self) -> dict[str, object]:
        degrees = [len(neighbors) for neighbors in self.adjacency.values()]
        return {
            "nodes": len(self.nodes),
            "edges": len(self.config.edges),
            "resources": sum(len(node.resources) for node in self.nodes.values()),
            "min_degree": min(degrees),
            "max_degree": max(degrees),
            "average_degree": sum(degrees) / len(degrees),
        }

    def to_dot(self, include_cache: bool = False) -> str:
        lines = [
            "graph p2p {",
            '  graph [overlap=false, splines=true, bgcolor="white"];',
            '  node [shape=box, style="rounded,filled", fillcolor="#e8f0fe", '
            'fontname="Arial"];',
            '  edge [color="#607d8b"];',
        ]
        for node_id in sorted(self.nodes, key=_natural_key):
            node = self.nodes[node_id]
            resource_text = ", ".join(sorted(node.resources, key=_natural_key))
            label = f"{node_id}\nRecursos: {resource_text}"
            if include_cache and node.cache:
                cache_text = ", ".join(
                    f"{resource}->{owner}"
                    for resource, owner in sorted(node.cache.items())
                )
                label += f"\nCache: {cache_text}"
            lines.append(
                f'  "{_dot_escape(node_id)}" [label="{_dot_escape(label)}"];'
            )

        for left, right in self.config.edges:
            lines.append(f'  "{_dot_escape(left)}" -- "{_dot_escape(right)}";')
        lines.append("}")
        return "\n".join(lines) + "\n"

    def write_dot(self, path: str | Path, include_cache: bool = False) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.to_dot(include_cache=include_cache), encoding="utf-8")
        return output


def _dot_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )
