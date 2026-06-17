from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Sequence

from .benchmark import (
    format_table,
    load_queries,
    run_benchmark,
    write_csv,
    write_svg_chart,
)
from .config import ConfigError, load_config
from .network import P2PNetwork
from .search import ALGORITHMS, SearchEngine, SearchResult, format_algorithm_options
from .simulator import SimulationResult, TopologySimulator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="p2p-search",
        description="Simulador de algoritmos de busca em redes P2P.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate", help="Valida e resume uma configuracao."
    )
    validate.add_argument("config", type=Path)

    search = subparsers.add_parser("search", help="Executa uma busca direta.")
    search.add_argument("config", type=Path)
    _add_search_arguments(search)
    search.add_argument("--seed", type=int, default=0)
    search.add_argument("--json", action="store_true", dest="as_json")

    simulate = subparsers.add_parser(
        "simulate",
        aliases=["simulator"],
        help="Carrega uma topologia P2P e executa uma busca no simulador.",
    )
    simulate.add_argument("topology", type=Path)
    simulate.add_argument("--node-id", "--node", dest="node_id")
    simulate.add_argument("--resource-id", "--resource", dest="resource_id")
    simulate.add_argument("--ttl", type=int)
    simulate.add_argument("--algorithm", "--algo", dest="algo")
    simulate.add_argument("--seed", type=int, default=0)
    simulate.add_argument("--json", action="store_true", dest="as_json")

    shell = subparsers.add_parser(
        "shell", help="Abre uma sessao interativa com cache persistente."
    )
    shell.add_argument("config", type=Path)
    shell.add_argument("--seed", type=int, default=0)

    graph = subparsers.add_parser(
        "graph", help="Exporta a topologia para Graphviz DOT."
    )
    graph.add_argument("config", type=Path)
    graph.add_argument("-o", "--output", type=Path, required=True)

    benchmark = subparsers.add_parser(
        "benchmark", help="Compara algoritmos com uma lista de consultas."
    )
    benchmark.add_argument("config", type=Path)
    benchmark.add_argument("queries", type=Path)
    benchmark.add_argument(
        "--algorithms",
        nargs="+",
        default=list(ALGORITHMS),
        help=f"Opcoes: {format_algorithm_options()}",
    )
    benchmark.add_argument("--runs", type=int, default=30)
    benchmark.add_argument("--seed", type=int, default=0)
    benchmark.add_argument("--csv", type=Path)
    benchmark.add_argument("--chart", type=Path)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            return _validate(args.config)
        if args.command == "search":
            return _search(args)
        if args.command in {"simulate", "simulator"}:
            return _simulate(args)
        if args.command == "shell":
            return _shell(args.config, args.seed)
        if args.command == "graph":
            return _graph(args.config, args.output)
        if args.command == "benchmark":
            return _benchmark(args)
    except (ConfigError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    return 1


def _load_network(config_path: Path) -> P2PNetwork:
    return P2PNetwork.from_config(load_config(config_path))


def _validate(config_path: Path) -> int:
    network = _load_network(config_path)
    summary = network.summary()
    print("Configuracao valida.")
    print(f"Nos: {summary['nodes']}")
    print(f"Arestas: {summary['edges']}")
    print(f"Recursos: {summary['resources']}")
    print(
        "Grau: "
        f"min={summary['min_degree']}, "
        f"max={summary['max_degree']}, "
        f"media={summary['average_degree']:.2f}"
    )
    return 0


def _search(args: argparse.Namespace) -> int:
    network = _load_network(args.config)
    result = SearchEngine(network, seed=args.seed).search(
        args.node_id,
        args.resource_id,
        args.ttl,
        args.algo,
    )
    if args.as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(_format_result(result))
    return 0 if result.found else 3


def _simulate(args: argparse.Namespace) -> int:
    simulator = TopologySimulator.from_topology_file(args.topology, seed=args.seed)
    node_id, resource_id, ttl, algorithm = _read_simulation_request(args)
    result = simulator.search(node_id, resource_id, ttl, algorithm)
    if args.as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(_format_simulation_result(result))
    return 0 if result.search.found else 3


def _read_simulation_request(
    args: argparse.Namespace,
) -> tuple[str, str, int, str]:
    node_id = args.node_id or _prompt("Node ID: ")
    resource_id = args.resource_id or _prompt("Recurso: ")
    ttl = args.ttl
    if ttl is None:
        ttl = int(_prompt("TTL: "))
    algorithm = args.algo or _prompt(
        f"Algoritmo ({format_algorithm_options()}): "
    )
    return node_id, resource_id, ttl, algorithm


def _prompt(label: str) -> str:
    try:
        return input(label).strip()
    except EOFError as exc:
        raise ValueError("Informe node id, recurso, ttl e algoritmo.") from exc


def _shell(config_path: Path, seed: int) -> int:
    network = _load_network(config_path)
    engine = SearchEngine(network, seed=seed)
    print("Rede carregada. Digite 'help' para ver os comandos.")

    while True:
        try:
            raw_command = input("p2p> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not raw_command:
            continue
        try:
            parts = shlex.split(raw_command)
        except ValueError as exc:
            print(f"Erro: {exc}")
            continue

        command = parts[0].lower()
        if command in {"quit", "exit"}:
            return 0
        if command == "help":
            print(_shell_help())
            continue
        if command == "nodes":
            _print_nodes(network)
            continue
        if command == "cache":
            node_id = parts[1] if len(parts) == 2 else None
            _print_cache(network, node_id)
            continue
        if command == "clear-cache":
            network.clear_caches()
            print("Caches limpos.")
            continue
        if command == "search":
            if len(parts) < 5:
                print("Uso: search NODE RESOURCE TTL ALGORITHM")
                continue
            try:
                result = engine.search(
                    parts[1],
                    parts[2],
                    int(parts[3]),
                    " ".join(parts[4:]),
                )
                print(_format_result(result))
            except ValueError as exc:
                print(f"Erro: {exc}")
            continue
        print(f"Comando desconhecido: {command}. Digite 'help'.")


def _graph(config_path: Path, output: Path) -> int:
    network = _load_network(config_path)
    network.write_dot(output)
    print(f"Topologia exportada para {output}.")
    return 0


def _benchmark(args: argparse.Namespace) -> int:
    network = _load_network(args.config)
    queries = load_queries(args.queries)
    summaries = run_benchmark(
        network,
        topology=args.config.stem,
        queries=queries,
        algorithms=args.algorithms,
        runs=args.runs,
        seed=args.seed,
    )
    print(format_table(summaries))
    if args.csv:
        write_csv(summaries, args.csv)
        print(f"\nCSV: {args.csv}")
    if args.chart:
        write_svg_chart(summaries, args.chart)
        print(f"Grafico: {args.chart}")
    return 0


def _format_result(result: SearchResult) -> str:
    status = "ENCONTRADO" if result.found else "NAO ENCONTRADO"
    lines = [
        f"Resultado: {status}",
        f"Algoritmo: {result.algorithm}",
        f"Origem/recurso/TTL: {result.origin} / {result.resource_id} / {result.ttl}",
        (
            "Mensagens: "
            f"{result.total_messages} "
            f"(consulta={result.query_messages}, resposta={result.response_messages})"
        ),
        f"Nos envolvidos: {result.nodes_involved} ({', '.join(result.involved_node_ids)})",
    ]
    if result.found:
        lines.extend(
            [
                f"Localizacao: {result.owner}",
                f"Respondido por: {result.responder} ({result.found_via})",
                f"Caminho: {' -> '.join(result.path)}",
            ]
        )
    else:
        lines.append(f"Motivo: {result.reason}")
        if result.path:
            lines.append(f"Passeio: {' -> '.join(result.path)}")
    return "\n".join(lines)


def _format_simulation_result(result: SimulationResult) -> str:
    summary = result.topology_summary
    lines = [
        f"Topologia: {result.topology}",
        (
            "Nos/arestas/recursos: "
            f"{summary['nodes']} / {summary['edges']} / {summary['resources']}"
        ),
        (
            "Grau: "
            f"min={summary['min_degree']}, "
            f"max={summary['max_degree']}, "
            f"media={summary['average_degree']:.2f}"
        ),
        "",
        _format_result(result.search),
    ]
    return "\n".join(lines)


def _print_nodes(network: P2PNetwork) -> None:
    for node_id in network.config.node_ids:
        resources = ", ".join(sorted(network.nodes[node_id].resources))
        neighbors = ", ".join(network.neighbors(node_id))
        print(f"{node_id}: recursos=[{resources}] vizinhos=[{neighbors}]")


def _print_cache(network: P2PNetwork, node_id: str | None) -> None:
    if node_id is not None and node_id not in network.nodes:
        print(f"Erro: no inexistente: {node_id}.")
        return
    node_ids = [node_id] if node_id else network.config.node_ids
    for current_id in node_ids:
        cache = network.nodes[current_id].cache
        entries = ", ".join(
            f"{resource}->{owner}" for resource, owner in sorted(cache.items())
        )
        print(f"{current_id}: {entries or '(vazio)'}")


def _shell_help() -> str:
    return "\n".join(
        [
            "search NODE RESOURCE TTL ALGORITHM  executa uma busca",
            "nodes                               lista nos, recursos e vizinhos",
            "cache [NODE]                        mostra os caches",
            "clear-cache                         limpa todos os caches",
            "help                                mostra esta ajuda",
            "quit                                encerra",
            f"Algoritmos: {format_algorithm_options()}",
        ]
    )


def _add_search_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("node_id")
    parser.add_argument("resource_id")
    parser.add_argument("ttl", type=int)
    parser.add_argument(
        "algo",
        metavar="algorithm",
        help=f"Opcoes: {format_algorithm_options()}",
    )


if __name__ == "__main__":
    raise SystemExit(main())
