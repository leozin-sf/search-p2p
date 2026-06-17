from __future__ import annotations

import csv
import json
import statistics
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Iterable, Sequence

from .network import P2PNetwork
from .search import ALGORITHMS, SearchEngine, normalize_algorithm


@dataclass(frozen=True)
class Query:
    node_id: str
    resource_id: str
    ttl: int


@dataclass(frozen=True)
class BenchmarkSummary:
    topology: str
    algorithm: str
    executions: int
    successes: int
    success_rate: float
    average_messages: float
    median_messages: float
    p95_messages: float
    average_nodes: float

    def to_dict(self) -> dict[str, object]:
        return {
            "topology": self.topology,
            "algorithm": self.algorithm,
            "executions": self.executions,
            "successes": self.successes,
            "success_rate": self.success_rate,
            "average_messages": self.average_messages,
            "median_messages": self.median_messages,
            "p95_messages": self.p95_messages,
            "average_nodes": self.average_nodes,
        }


def load_queries(path: str | Path) -> list[Query]:
    query_path = Path(path)
    try:
        data = json.loads(query_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Nao foi possivel ler '{query_path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON invalido em {query_path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, list) or not data:
        raise ValueError("O arquivo de consultas deve conter uma lista nao vazia.")

    queries: list[Query] = []
    errors: list[str] = []
    for index, raw_query in enumerate(data):
        if not isinstance(raw_query, dict):
            errors.append(f"Consulta {index} deve ser um objeto.")
            continue
        query_errors: list[str] = []
        node_id = raw_query.get("node_id")
        resource_id = raw_query.get("resource_id")
        ttl = raw_query.get("ttl")
        if not isinstance(node_id, str) or not node_id.strip():
            query_errors.append(f"Consulta {index}: node_id invalido.")
        if not isinstance(resource_id, str) or not resource_id.strip():
            query_errors.append(f"Consulta {index}: resource_id invalido.")
        if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl < 0:
            query_errors.append(
                f"Consulta {index}: ttl deve ser inteiro nao negativo."
            )
        errors.extend(query_errors)
        if not query_errors:
            queries.append(Query(node_id.strip(), resource_id.strip(), ttl))

    if errors:
        raise ValueError("\n".join(errors))
    return queries


def run_benchmark(
    network: P2PNetwork,
    topology: str,
    queries: Sequence[Query],
    algorithms: Sequence[str] = ALGORITHMS,
    runs: int = 1,
    seed: int = 0,
) -> list[BenchmarkSummary]:
    if runs <= 0:
        raise ValueError("runs deve ser maior que zero.")
    if not queries:
        raise ValueError("E necessario informar ao menos uma consulta.")
    normalized_algorithms = tuple(
        normalize_algorithm(algorithm) for algorithm in algorithms
    )

    summaries: list[BenchmarkSummary] = []
    for algorithm in normalized_algorithms:
        messages: list[int] = []
        nodes: list[int] = []
        successes = 0

        for run_index in range(runs):
            run_network = network.clone()
            for query_index, query in enumerate(queries):
                # Equal seeds make random and informed random walks comparable.
                query_seed = seed + run_index * 10_007 + query_index * 101
                engine = SearchEngine(run_network, seed=query_seed)
                result = engine.search(
                    query.node_id,
                    query.resource_id,
                    query.ttl,
                    algorithm,
                )
                messages.append(result.total_messages)
                nodes.append(result.nodes_involved)
                successes += int(result.found)

        executions = len(messages)
        summaries.append(
            BenchmarkSummary(
                topology=topology,
                algorithm=algorithm,
                executions=executions,
                successes=successes,
                success_rate=successes / executions,
                average_messages=statistics.fmean(messages),
                median_messages=statistics.median(messages),
                p95_messages=_percentile(messages, 0.95),
                average_nodes=statistics.fmean(nodes),
            )
        )
    return summaries


def write_csv(
    summaries: Iterable[BenchmarkSummary], path: str | Path
) -> Path:
    rows = [summary.to_dict() for summary in summaries]
    if not rows:
        raise ValueError("Nao ha resultados para exportar.")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return output


def write_svg_chart(
    summaries: Sequence[BenchmarkSummary], path: str | Path
) -> Path:
    if not summaries:
        raise ValueError("Nao ha resultados para gerar o grafico.")

    width = 980
    height = 520
    margin_left = 85
    margin_right = 35
    margin_top = 75
    margin_bottom = 125
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom
    max_messages = max(summary.average_messages for summary in summaries) or 1
    bar_slot = chart_width / len(summaries)
    bar_width = min(110, bar_slot * 0.62)
    colors = {
        "flooding": "#1565c0",
        "informed_flooding": "#42a5f5",
        "random_walk": "#ef6c00",
        "informed_random_walk": "#ffb74d",
    }

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">'
        ),
        '<rect width="100%" height="100%" fill="white"/>',
        (
            '<text x="490" y="34" text-anchor="middle" '
            'font-family="Arial" font-size="22" font-weight="bold">'
            "Media de mensagens por algoritmo</text>"
        ),
        (
            f'<text x="490" y="58" text-anchor="middle" font-family="Arial" '
            f'font-size="14">{escape(summaries[0].topology)}</text>'
        ),
    ]

    for tick in range(6):
        value = max_messages * tick / 5
        y = margin_top + chart_height - chart_height * tick / 5
        lines.extend(
            [
                (
                    f'<line x1="{margin_left}" y1="{y:.1f}" '
                    f'x2="{width - margin_right}" y2="{y:.1f}" '
                    'stroke="#e0e0e0"/>'
                ),
                (
                    f'<text x="{margin_left - 10}" y="{y + 5:.1f}" '
                    'text-anchor="end" font-family="Arial" font-size="12">'
                    f"{value:.1f}</text>"
                ),
            ]
        )

    for index, summary in enumerate(summaries):
        x = margin_left + bar_slot * index + (bar_slot - bar_width) / 2
        bar_height = chart_height * summary.average_messages / max_messages
        y = margin_top + chart_height - bar_height
        color = colors.get(summary.algorithm, "#607d8b")
        label_x = x + bar_width / 2
        lines.extend(
            [
                (
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                    f'height="{bar_height:.1f}" fill="{color}" rx="4"/>'
                ),
                (
                    f'<text x="{label_x:.1f}" y="{max(y - 8, 70):.1f}" '
                    'text-anchor="middle" font-family="Arial" font-size="13" '
                    f'font-weight="bold">{summary.average_messages:.2f}</text>'
                ),
                (
                    f'<text x="{label_x:.1f}" y="{margin_top + chart_height + 22}" '
                    'text-anchor="middle" font-family="Arial" font-size="12">'
                    f"{escape(summary.algorithm)}</text>"
                ),
                (
                    f'<text x="{label_x:.1f}" y="{margin_top + chart_height + 42}" '
                    'text-anchor="middle" font-family="Arial" font-size="11" '
                    f'fill="#555">sucesso: {summary.success_rate:.1%}</text>'
                ),
            ]
        )

    lines.extend(
        [
            (
                f'<line x1="{margin_left}" y1="{margin_top + chart_height}" '
                f'x2="{width - margin_right}" y2="{margin_top + chart_height}" '
                'stroke="#333"/>'
            ),
            (
                f'<text x="20" y="{margin_top + chart_height / 2}" '
                'text-anchor="middle" font-family="Arial" font-size="13" '
                'transform="rotate(-90 20 '
                f'{margin_top + chart_height / 2})">Mensagens</text>'
            ),
            (
                f'<text x="490" y="{height - 24}" text-anchor="middle" '
                'font-family="Arial" font-size="11" fill="#555">'
                "Mensagens = requisicoes entre nos + respostas ate o iniciador"
                "</text>"
            ),
            "</svg>",
        ]
    )

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def format_table(summaries: Sequence[BenchmarkSummary]) -> str:
    headers = (
        "algoritmo",
        "execucoes",
        "sucesso",
        "media msg",
        "mediana",
        "p95",
        "media nos",
    )
    rows = [
        (
            summary.algorithm,
            str(summary.executions),
            f"{summary.success_rate:.1%}",
            f"{summary.average_messages:.2f}",
            f"{summary.median_messages:.2f}",
            f"{summary.p95_messages:.2f}",
            f"{summary.average_nodes:.2f}",
        )
        for summary in summaries
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    def render(row: Sequence[str]) -> str:
        return " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(row)
        )

    separator = "-+-".join("-" * width for width in widths)
    return "\n".join([render(headers), separator, *(render(row) for row in rows)])


def _percentile(values: Sequence[int], quantile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction
