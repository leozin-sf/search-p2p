"""Simulador de algoritmos de busca em redes P2P nao estruturadas."""

from .config import ConfigError, NetworkConfig, load_config
from .network import P2PNetwork
from .search import (
    ALGORITHMS,
    SearchEngine,
    SearchResult,
    format_algorithm_options,
    normalize_algorithm,
)
from .simulator import SimulationResult, TopologySimulator

__all__ = [
    "ALGORITHMS",
    "ConfigError",
    "NetworkConfig",
    "P2PNetwork",
    "SearchEngine",
    "SearchResult",
    "SimulationResult",
    "TopologySimulator",
    "format_algorithm_options",
    "load_config",
    "normalize_algorithm",
]
