from p2p_search.config import load_config
from p2p_search.network import P2PNetwork
from p2p_search.search import SearchEngine

network = P2PNetwork.from_config(load_config('examples/ring_12.json'))
engine = SearchEngine(network, seed=2026)

print('=== search n1 r7 6 flooding ===')
r = engine.search('n1', 'r7', 6, 'flooding')
status = 'ENCONTRADO' if r.found else 'NAO ENCONTRADO'
print(f'Resultado: {status}')
print(f'Algoritmo: {r.algorithm}')
print(f'Mensagens: {r.total_messages} (consulta={r.query_messages}, resposta={r.response_messages})')
print(f'Nos envolvidos: {r.nodes_involved} ({", ".join(r.involved_node_ids)})')
if r.found:
    print(f'Localizacao: {r.owner}')
    print(f'Caminho: {" -> ".join(r.path)}')

print()
print('=== cache n1 ===')
cache = network.nodes['n1'].cache
if cache:
    entries = ', '.join(f'{res}->{owner}' for res, owner in sorted(cache.items()))
else:
    entries = '(vazio)'
print(f'n1: {entries}')

print()
print('=== search n1 r7 6 informed_flooding ===')
r2 = engine.search('n1', 'r7', 6, 'informed_flooding')
status2 = 'ENCONTRADO' if r2.found else 'NAO ENCONTRADO'
print(f'Resultado: {status2}')
print(f'Algoritmo: {r2.algorithm}')
print(f'Mensagens: {r2.total_messages} (consulta={r2.query_messages}, resposta={r2.response_messages})')
print(f'Nos envolvidos: {r2.nodes_involved} ({", ".join(r2.involved_node_ids)})')
if r2.found:
    print(f'Localizacao: {r2.owner}')
    print(f'Caminho: {" -> ".join(r2.path)}')
