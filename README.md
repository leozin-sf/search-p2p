# Trabalho 7 - Algoritmos de Busca em Sistemas P2P

## Integrantes

| Nome | Matricula |
|------|:---------:|
| Leonardo Silva | 2319973 |
| Ravi Freitas | 2316154 |
| Luca Solon | 1910486 |
| Luiz Henrique | 2520528 |

Simulador de uma rede P2P nao estruturada a partir de uma topologia. Depois de
carregar a topologia, voce informa o node id inicial, o recurso, o TTL e o
algoritmo de busca. O projeto tambem valida a topologia, mantem cache
distribuido e implementa os quatro algoritmos pedidos no enunciado:

- `flooding`
- `informed flooding`
- `random walk`
- `informed random walk`

Os nomes tambem sao aceitos com `_`, por exemplo `informed_flooding`.

O projeto usa apenas a biblioteca padrao do Python 3.10+. PyYAML e Graphviz
sao opcionais.

## Execucao

Validar uma topologia:

```bash
python3 -m p2p_search validate examples/ring_12.json
```

Executar uma busca no simulador a partir de uma topologia:

```bash
python3 -m p2p_search simulate \
  examples/ring_12.json \
  --node-id n1 \
  --resource-id r7 \
  --ttl 6 \
  --algorithm "informed flooding"
```

Tambem e possivel chamar o alias `simulator` ou usar o atalho direto `search`:

```bash
python3 -m p2p_search search \
  examples/ring_12.json n1 r7 6 "random walk"
```

Abrir a demonstracao interativa, na qual os caches persistem entre buscas:

```bash
python3 -m p2p_search shell examples/ring_12.json --seed 2026
```

Dentro do shell:

```text
search n1 r7 6 flooding
cache n1
search n1 r7 6 informed flooding
clear-cache
nodes
quit
```

Comparar os algoritmos e gerar CSV e grafico SVG:

```bash
python3 -m p2p_search benchmark \
  examples/ring_12.json examples/queries.json \
  --runs 100 --seed 2026 \
  --csv docs/results/ring_12.csv \
  --chart docs/results/ring_12.svg
```

Todos os experimentos da entrega podem ser reproduzidos com:

```bash
./scripts/run_experiments.sh
```

## Formato da configuracao

O formato principal e JSON. Recursos tambem podem ser escritos como uma string
separada por virgulas. YAML e aceito quando PyYAML esta instalado.

```json
{
  "num_nodes": 3,
  "min_neighbors": 1,
  "max_neighbors": 2,
  "resources": {
    "n1": ["r1"],
    "n2": ["r2"],
    "n3": ["r3"]
  },
  "edges": [
    ["n1", "n2"],
    ["n2", "n3"]
  ]
}
```

As validacoes detectam:

- rede particionada;
- grau fora dos limites minimo e maximo;
- no sem recurso;
- laco de um no para ele mesmo;
- quantidade incorreta de nos;
- aresta duplicada ou apontando para no inexistente;
- campos e tipos invalidos.

## Semantica da simulacao

O TTL e o numero maximo de saltos da mensagem de consulta. O no inicial e
verificado com TTL zero.

No flooding, cada no encaminha a consulta uma unica vez, para todos os vizinhos
exceto aquele do qual recebeu a primeira copia. Copias duplicadas enviadas por
ciclos contam como mensagens, mas nao sao retransmitidas novamente.

No random walk, um unico vizinho e escolhido uniformemente a cada salto. O
passeio pode revisitar nos.

Quando o recurso e encontrado, a localizacao retorna pelo caminho da consulta.
Por isso:

```text
total de mensagens = mensagens de consulta + mensagens de resposta
```

Todos os nos no caminho da resposta aprendem `recurso -> no proprietario`.
Algoritmos comuns atualizam esse cache, mas somente os algoritmos informados o
consultam. O numero de nos envolvidos conta IDs distintos.

## Experimentos

Foram usadas tres redes de 12 nos e dez consultas, sendo cinco repeticoes para
medir o ganho do cache. Cada algoritmo executou 1.000 buscas por topologia
(10 consultas x 100 rodadas), com semente `2026`.

| Topologia | Algoritmo | Media de mensagens | Sucesso |
|---|---|---:|---:|
| Anel, grau 2 | flooding | 17,40 | 100,0% |
| Anel, grau 2 | informed_flooding | 8,70 | 100,0% |
| Anel, grau 2 | random_walk | 13,16 | 17,9% |
| Anel, grau 2 | informed_random_walk | 11,83 | 26,2% |
| Circulante, grau 3 | flooding | 5,40 | 100,0% |
| Circulante, grau 3 | informed_flooding | 2,70 | 100,0% |
| Circulante, grau 3 | random_walk | 8,94 | 70,1% |
| Circulante, grau 3 | informed_random_walk | 5,83 | 80,7% |
| Circulante, grau 4 | flooding | 31,00 | 100,0% |
| Circulante, grau 4 | informed_flooding | 15,50 | 100,0% |
| Circulante, grau 4 | random_walk | 13,23 | 46,7% |
| Circulante, grau 4 | informed_random_walk | 10,18 | 57,3% |

Os resultados completos estao em `docs/results/`. A topologia de grau 4 deixa
claro que mais vizinhos nao garantem menor custo para flooding: as muitas copias
enviadas em ciclos aumentaram o trafego, apesar das distancias menores.

## Representacao grafica

Exportar a rede para DOT:

```bash
python3 -m p2p_search graph \
  examples/circulant_3_12.json \
  --output docs/results/topology.dot
```

Com Graphviz instalado, o DOT pode ser convertido:

```bash
dot -Tsvg docs/results/topology.dot -o docs/results/topology.svg
```

## Testes

```bash
python3 -m unittest discover -v
```

A suite possui 29 testes cobrindo configuracao, conectividade, graus, recursos,
TTL, contagem de mensagens, cache, passeio aleatorio e benchmark.

## Entrega

A apresentacao esta em `docs/apresentacao.html`. Abra o arquivo em um navegador,
use as setas para navegar e imprima como PDF se necessario. Antes da entrega,
substitua os campos de integrantes no segundo slide.
