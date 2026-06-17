"""Gera SVG visual da topologia P2P sem dependencias externas."""
import json
import math
import sys
from pathlib import Path


def draw(config_path: Path, output_path: Path) -> None:
    with open(config_path) as f:
        cfg = json.load(f)

    nodes = [f"n{i+1}" for i in range(cfg["num_nodes"])]
    edges = [tuple(e) for e in cfg["edges"]]
    resources = cfg.get("resources", {})

    n = len(nodes)
    cx, cy, r = 300, 300, 230
    angle_step = 2 * math.pi / n

    # posicoes em circulo
    pos = {}
    for i, node in enumerate(nodes):
        angle = -math.pi / 2 + i * angle_step
        pos[node] = (cx + r * math.cos(angle), cy + r * math.sin(angle))

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="640">')
    lines.append('<rect width="600" height="640" fill="#f8f9fa"/>')

    # titulo
    title = config_path.stem.replace("_", " ").title()
    lines.append(f'<text x="300" y="30" text-anchor="middle" font-family="sans-serif" font-size="16" font-weight="bold" fill="#333">{title}</text>')

    # arestas
    drawn = set()
    for a, b in edges:
        key = tuple(sorted([a, b]))
        if key in drawn:
            continue
        drawn.add(key)
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#adb5bd" stroke-width="1.5"/>')

    # nos
    for node in nodes:
        x, y = pos[node]
        res = resources.get(node, [])
        color = "#4361ee" if res else "#adb5bd"
        # circulo
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="22" fill="{color}" stroke="white" stroke-width="2"/>')
        # id do no
        lines.append(f'<text x="{x:.1f}" y="{y:.1f}" dy="0.35em" text-anchor="middle" font-family="sans-serif" font-size="11" font-weight="bold" fill="white">{node}</text>')
        # recursos abaixo do no
        if res:
            res_str = ",".join(res)
            # posiciona label fora do circulo
            dx = x - cx
            dy = y - cy
            dist = math.hypot(dx, dy)
            lx = x + (dx / dist) * 32
            ly = y + (dy / dist) * 32
            lines.append(f'<text x="{lx:.1f}" y="{ly:.1f}" dy="0.35em" text-anchor="middle" font-family="sans-serif" font-size="8" fill="#555">{res_str}</text>')

    # legenda
    lines.append('<circle cx="30" cy="610" r="8" fill="#4361ee"/>')
    lines.append('<text x="44" y="614" font-family="sans-serif" font-size="11" fill="#333">No com recurso</text>')
    lines.append(f'<text x="300" y="630" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#888">Nos: {n}  |  Arestas: {len(drawn)}</text>')

    lines.append('</svg>')

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"SVG gerado: {output_path}")


if __name__ == "__main__":
    configs = [
        ("examples/ring_12.json", "docs/results/topo_ring_12.svg"),
        ("examples/circulant_3_12.json", "docs/results/topo_circulant_3_12.svg"),
        ("examples/circulant_4_12.json", "docs/results/topo_circulant_4_12.svg"),
    ]
    for cfg, out in configs:
        draw(Path(cfg), Path(out))
