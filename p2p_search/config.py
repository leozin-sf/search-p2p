from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a network configuration is invalid."""

    def __init__(self, errors: list[str] | str):
        self.errors = [errors] if isinstance(errors, str) else errors
        super().__init__("\n".join(self.errors))


@dataclass(frozen=True)
class NetworkConfig:
    num_nodes: int
    min_neighbors: int
    max_neighbors: int
    resources: dict[str, frozenset[str]]
    edges: tuple[tuple[str, str], ...]

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.resources, key=_natural_key))


def load_config(path: str | Path) -> NetworkConfig:
    config_path = Path(path)
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Nao foi possivel ler '{config_path}': {exc}") from exc

    suffix = config_path.suffix.lower()
    try:
        if suffix == ".json":
            data = json.loads(raw_text)
        elif suffix in {".yaml", ".yml"}:
            data = _load_yaml(raw_text)
        else:
            raise ConfigError(
                "Formato nao suportado. Use um arquivo .json, .yaml ou .yml."
            )
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"JSON invalido em {config_path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc

    return parse_config(data)


def parse_config(data: Any) -> NetworkConfig:
    if not isinstance(data, dict):
        raise ConfigError("A raiz da configuracao deve ser um objeto.")

    errors: list[str] = []
    num_nodes = _read_int(data, "num_nodes", errors)
    min_neighbors = _read_int(data, "min_neighbors", errors)
    max_neighbors = _read_int(data, "max_neighbors", errors)
    resources = _read_resources(data.get("resources"), errors)
    edges = _read_edges(data.get("edges"), errors)

    if errors:
        raise ConfigError(errors)

    assert num_nodes is not None
    assert min_neighbors is not None
    assert max_neighbors is not None

    if num_nodes <= 0:
        errors.append("num_nodes deve ser maior que zero.")
    if min_neighbors < 0:
        errors.append("min_neighbors nao pode ser negativo.")
    if max_neighbors < 0:
        errors.append("max_neighbors nao pode ser negativo.")
    if min_neighbors > max_neighbors:
        errors.append("min_neighbors nao pode ser maior que max_neighbors.")
    if num_nodes > 0 and max_neighbors >= num_nodes:
        errors.append("max_neighbors deve ser menor que num_nodes.")
    if len(resources) != num_nodes:
        errors.append(
            f"num_nodes declara {num_nodes}, mas resources define {len(resources)} nos."
        )

    node_ids = set(resources)
    adjacency = {node_id: set() for node_id in node_ids}
    seen_edges: set[frozenset[str]] = set()
    valid_edges: list[tuple[str, str]] = []

    for left, right in edges:
        if left == right:
            errors.append(f"Aresta invalida ({left}, {right}): laco nao permitido.")
            continue
        unknown = sorted({left, right} - node_ids, key=_natural_key)
        if unknown:
            errors.append(
                f"Aresta ({left}, {right}) referencia no(s) inexistente(s): "
                + ", ".join(unknown)
            )
            continue
        edge_key = frozenset((left, right))
        if edge_key in seen_edges:
            errors.append(f"Aresta duplicada: ({left}, {right}).")
            continue
        seen_edges.add(edge_key)
        adjacency[left].add(right)
        adjacency[right].add(left)
        valid_edges.append((left, right))

    for node_id in sorted(node_ids, key=_natural_key):
        degree = len(adjacency[node_id])
        if degree < min_neighbors or degree > max_neighbors:
            errors.append(
                f"No {node_id} possui {degree} vizinho(s); esperado entre "
                f"{min_neighbors} e {max_neighbors}."
            )

    if node_ids and not _is_connected(adjacency):
        errors.append("A rede esta particionada: nem todos os nos sao alcancaveis.")

    if errors:
        raise ConfigError(errors)

    normalized_edges = tuple(
        sorted(
            (tuple(sorted(edge, key=_natural_key)) for edge in valid_edges),
            key=lambda edge: (_natural_key(edge[0]), _natural_key(edge[1])),
        )
    )
    return NetworkConfig(
        num_nodes=num_nodes,
        min_neighbors=min_neighbors,
        max_neighbors=max_neighbors,
        resources=resources,
        edges=normalized_edges,
    )


def _read_int(data: dict[str, Any], field: str, errors: list[str]) -> int | None:
    value = data.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"{field} deve ser um numero inteiro.")
        return None
    return value


def _read_resources(
    value: Any, errors: list[str]
) -> dict[str, frozenset[str]]:
    if not isinstance(value, dict):
        errors.append("resources deve ser um objeto no -> lista de recursos.")
        return {}

    resources: dict[str, frozenset[str]] = {}
    for raw_node_id, raw_resources in value.items():
        if not isinstance(raw_node_id, str) or not raw_node_id.strip():
            errors.append("Todo identificador de no deve ser uma string nao vazia.")
            continue
        node_id = raw_node_id.strip()
        if node_id in resources:
            errors.append(f"Identificador de no duplicado: {node_id}.")
            continue

        if isinstance(raw_resources, str):
            items = [item.strip() for item in raw_resources.split(",")]
        elif isinstance(raw_resources, list):
            items = raw_resources
        else:
            errors.append(
                f"Recursos de {node_id} devem ser uma lista ou string separada por virgulas."
            )
            continue

        normalized: list[str] = []
        invalid = False
        for item in items:
            if not isinstance(item, str) or not item.strip():
                errors.append(
                    f"Todo recurso de {node_id} deve ser uma string nao vazia."
                )
                invalid = True
                continue
            normalized.append(item.strip())

        if invalid and not normalized:
            resources[node_id] = frozenset()
            continue
        if not normalized:
            errors.append(f"No {node_id} nao possui recursos.")
        if len(set(normalized)) != len(normalized):
            errors.append(f"No {node_id} possui recursos duplicados.")
        resources[node_id] = frozenset(normalized)

    return resources


def _read_edges(value: Any, errors: list[str]) -> list[tuple[str, str]]:
    if not isinstance(value, list):
        errors.append("edges deve ser uma lista de pares de nos.")
        return []

    edges: list[tuple[str, str]] = []
    for index, edge in enumerate(value):
        if (
            not isinstance(edge, (list, tuple))
            or len(edge) != 2
            or not all(isinstance(node, str) and node.strip() for node in edge)
        ):
            errors.append(
                f"Aresta na posicao {index} deve conter exatamente dois IDs de nos."
            )
            continue
        edges.append((edge[0].strip(), edge[1].strip()))
    return edges


def _is_connected(adjacency: dict[str, set[str]]) -> bool:
    start = next(iter(adjacency))
    visited = {start}
    pending = [start]
    while pending:
        current = pending.pop()
        for neighbor in adjacency[current] - visited:
            visited.add(neighbor)
            pending.append(neighbor)
    return len(visited) == len(adjacency)


def _load_yaml(raw_text: str) -> Any:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ConfigError(
            "Arquivos YAML exigem PyYAML. Use JSON ou instale com 'pip install PyYAML'."
        ) from exc

    try:
        return yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML invalido: {exc}") from exc


def _natural_key(value: str) -> tuple[tuple[int, object], ...]:
    parts: list[tuple[int, object]] = []
    current = ""
    digit_mode: bool | None = None
    for character in value:
        is_digit = character.isdigit()
        if digit_mode is not None and is_digit != digit_mode:
            parts.append(
                (1, int(current)) if digit_mode else (0, current.lower())
            )
            current = ""
        current += character
        digit_mode = is_digit
    if current:
        parts.append((1, int(current)) if digit_mode else (0, current.lower()))
    return tuple(parts)
