from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Literal

from .config import _natural_key
from .network import P2PNetwork

Algorithm = Literal[
    "flooding",
    "informed_flooding",
    "random_walk",
    "informed_random_walk",
]

ALGORITHMS: tuple[Algorithm, ...] = (
    "flooding",
    "informed_flooding",
    "random_walk",
    "informed_random_walk",
)


@dataclass(frozen=True)
class SearchResult:
    algorithm: str
    origin: str
    resource_id: str
    ttl: int
    found: bool
    owner: str | None
    responder: str | None
    found_via: str | None
    query_messages: int
    response_messages: int
    total_messages: int
    nodes_involved: int
    involved_node_ids: tuple[str, ...]
    path: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["involved_node_ids"] = list(self.involved_node_ids)
        result["path"] = list(self.path)
        return result


class SearchEngine:
    def __init__(self, network: P2PNetwork, seed: int | None = None):
        self.network = network
        self.rng = random.Random(seed)

    def search(
        self,
        node_id: str,
        resource_id: str,
        ttl: int,
        algorithm: str,
    ) -> SearchResult:
        self._validate_request(node_id, resource_id, ttl, algorithm)
        informed = algorithm.startswith("informed_")

        if algorithm in {"flooding", "informed_flooding"}:
            return self._flooding(node_id, resource_id, ttl, algorithm, informed)
        return self._random_walk(node_id, resource_id, ttl, algorithm, informed)

    def _flooding(
        self,
        origin: str,
        resource_id: str,
        ttl: int,
        algorithm: str,
        informed: bool,
    ) -> SearchResult:
        query_messages = 0
        involved = {origin}
        visited = {origin}
        parent: dict[str, str | None] = {origin: None}
        frontier = [origin]

        for depth in range(ttl + 1):
            matches: list[
                tuple[int, tuple[tuple[int, object], ...], str, str, str]
            ] = []
            for node_id in frontier:
                match = self._lookup(node_id, resource_id, informed)
                if match is not None:
                    owner, found_via = match
                    local_priority = 0 if found_via == "resource" else 1
                    matches.append(
                        (
                            local_priority,
                            _natural_key(node_id),
                            node_id,
                            owner,
                            found_via,
                        )
                    )

            if matches:
                _, _, responder, owner, found_via = min(matches)
                path = self._reconstruct_path(parent, responder)
                response_messages = len(path) - 1
                self._update_cache(path, resource_id, owner)
                return self._result(
                    algorithm=algorithm,
                    origin=origin,
                    resource_id=resource_id,
                    ttl=ttl,
                    found=True,
                    owner=owner,
                    responder=responder,
                    found_via=found_via,
                    query_messages=query_messages,
                    response_messages=response_messages,
                    involved=involved,
                    path=path,
                    reason="found",
                )

            if depth == ttl:
                break

            next_frontier: list[str] = []
            for current in sorted(frontier, key=_natural_key):
                previous = parent[current]
                for neighbor in self.network.neighbors(current):
                    if neighbor == previous:
                        continue
                    query_messages += 1
                    involved.add(neighbor)
                    if neighbor not in visited:
                        visited.add(neighbor)
                        parent[neighbor] = current
                        next_frontier.append(neighbor)
            frontier = next_frontier
            if not frontier:
                break

        return self._not_found_result(
            algorithm,
            origin,
            resource_id,
            ttl,
            query_messages,
            involved,
        )

    def _random_walk(
        self,
        origin: str,
        resource_id: str,
        ttl: int,
        algorithm: str,
        informed: bool,
    ) -> SearchResult:
        current = origin
        path = [origin]
        involved = {origin}
        query_messages = 0

        for depth in range(ttl + 1):
            match = self._lookup(current, resource_id, informed)
            if match is not None:
                owner, found_via = match
                response_messages = len(path) - 1
                self._update_cache(path, resource_id, owner)
                return self._result(
                    algorithm=algorithm,
                    origin=origin,
                    resource_id=resource_id,
                    ttl=ttl,
                    found=True,
                    owner=owner,
                    responder=current,
                    found_via=found_via,
                    query_messages=query_messages,
                    response_messages=response_messages,
                    involved=involved,
                    path=tuple(path),
                    reason="found",
                )

            if depth == ttl:
                break
            neighbors = self.network.neighbors(current)
            if not neighbors:
                break
            current = self.rng.choice(neighbors)
            path.append(current)
            involved.add(current)
            query_messages += 1

        return self._not_found_result(
            algorithm,
            origin,
            resource_id,
            ttl,
            query_messages,
            involved,
            path=tuple(path),
        )

    def _lookup(
        self, node_id: str, resource_id: str, informed: bool
    ) -> tuple[str, str] | None:
        node = self.network.nodes[node_id]
        if resource_id in node.resources:
            return node_id, "resource"
        if informed and resource_id in node.cache:
            return node.cache[resource_id], "cache"
        return None

    def _update_cache(
        self, path: tuple[str, ...] | list[str], resource_id: str, owner: str
    ) -> None:
        # Every node on the reply route learns the resource location.
        for node_id in path:
            self.network.nodes[node_id].cache[resource_id] = owner

    def _not_found_result(
        self,
        algorithm: str,
        origin: str,
        resource_id: str,
        ttl: int,
        query_messages: int,
        involved: set[str],
        path: tuple[str, ...] = (),
    ) -> SearchResult:
        reason = (
            "resource_absent"
            if not self.network.owners(resource_id)
            else "ttl_exhausted"
        )
        return self._result(
            algorithm=algorithm,
            origin=origin,
            resource_id=resource_id,
            ttl=ttl,
            found=False,
            owner=None,
            responder=None,
            found_via=None,
            query_messages=query_messages,
            response_messages=0,
            involved=involved,
            path=path,
            reason=reason,
        )

    @staticmethod
    def _reconstruct_path(
        parent: dict[str, str | None], destination: str
    ) -> tuple[str, ...]:
        reversed_path = [destination]
        current = destination
        while parent[current] is not None:
            current = parent[current]  # type: ignore[assignment]
            reversed_path.append(current)
        return tuple(reversed(reversed_path))

    @staticmethod
    def _result(
        *,
        algorithm: str,
        origin: str,
        resource_id: str,
        ttl: int,
        found: bool,
        owner: str | None,
        responder: str | None,
        found_via: str | None,
        query_messages: int,
        response_messages: int,
        involved: set[str],
        path: tuple[str, ...] | list[str],
        reason: str,
    ) -> SearchResult:
        return SearchResult(
            algorithm=algorithm,
            origin=origin,
            resource_id=resource_id,
            ttl=ttl,
            found=found,
            owner=owner,
            responder=responder,
            found_via=found_via,
            query_messages=query_messages,
            response_messages=response_messages,
            total_messages=query_messages + response_messages,
            nodes_involved=len(involved),
            involved_node_ids=tuple(sorted(involved, key=_natural_key)),
            path=tuple(path),
            reason=reason,
        )

    def _validate_request(
        self, node_id: str, resource_id: str, ttl: int, algorithm: str
    ) -> None:
        if node_id not in self.network.nodes:
            raise ValueError(f"No inicial inexistente: {node_id}.")
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise ValueError("resource_id deve ser uma string nao vazia.")
        if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl < 0:
            raise ValueError("ttl deve ser um inteiro maior ou igual a zero.")
        if algorithm not in ALGORITHMS:
            raise ValueError(
                f"Algoritmo invalido: {algorithm}. Opcoes: {', '.join(ALGORITHMS)}."
            )
