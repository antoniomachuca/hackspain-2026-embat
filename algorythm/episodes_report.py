"""Medición básica de episodios: anticipación, avisos tardíos, no confirmados y pendientes.

Run: python -m algorythm.episodes_report
Lee engine_results/episodes.json y escribe engine_results/episodes_report.md.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from algorythm.score_episodes import month_diff

ROOT = Path(__file__).resolve().parents[1]


def summarize(data):
    episodes = [e for c in data['companies'].values() for e in c['episodios']]
    report = {'empresas': len(data['companies']),
              'empresas_con_episodio': sum(1 for c in data['companies'].values() if c['episodios']),
              'episodios': len(episodes), 'direcciones': {}}
    for direction in ('deterioro', 'mejora'):
        rows = [e for e in episodes if e['direccion'] == direction]
        lead = np.array([e['meses_anticipacion'] for e in rows if e['meses_anticipacion'] is not None])
        durations = [month_diff(e['cierre'], e['deteccion']) for e in rows if e['cierre']]
        report['direcciones'][direction] = {
            'episodios': len(rows),
            'confirmacion': dict(Counter(e['estado_confirmacion'] for e in rows)),
            'estado': dict(Counter(e['estado'] for e in rows)),
            'criterio': dict(Counter(e['criterio'] for e in rows if e['criterio'])),
            'anticipacion': {'n': int(len(lead)), 'histograma': {int(k): int(v) for k, v in sorted(Counter(lead.tolist()).items())},
                             'mediana': float(np.median(lead)) if len(lead) else None,
                             'aviso_antes': float(np.mean(lead > 0)) if len(lead) else None,
                             'mismo_mes': float(np.mean(lead == 0)) if len(lead) else None,
                             'aviso_tardio': float(np.mean(lead < 0)) if len(lead) else None},
            'con_escalada': sum(1 for e in rows if e['escaladas']),
            'senales': dict(Counter(s['senal'] for e in rows for s in e['senales'])),
            'duracion_mediana_meses': float(np.median(durations)) if durations else None,
            'motivo_cierre': dict(Counter(e['motivo_cierre'] for e in rows if e['cierre'])),
        }
    return report


def markdown(report, as_of):
    lines = [f'# Medición de episodios · corte {as_of}', '',
             f"{report['empresas']} empresas, {report['empresas_con_episodio']} con al menos un episodio, {report['episodios']} episodios.", '',
             'Anticipación = cambio material − detección (meses). Negativa = el cambio material se confirmó antes del aviso.',
             'Se cuentan también los avisos no confirmados y pendientes; no solo los aciertos.', '',
             '| Dirección | Episodios | Confirmados | No confirmados | Pendientes | Anticipación mediana | Aviso antes | Mismo mes | Aviso tardío |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for direction, r in report['direcciones'].items():
        c, a = r['confirmacion'], r['anticipacion']
        pct = lambda v: '—' if v is None else f'{v:.0%}'
        lines.append(f"| {direction} | {r['episodios']} | {c.get('confirmado', 0)} | {c.get('no_confirmado', 0)} | {c.get('pendiente', 0)} | "
                     f"{a['mediana'] if a['mediana'] is not None else '—'} | {pct(a['aviso_antes'])} | {pct(a['mismo_mes'])} | {pct(a['aviso_tardio'])} |")
    lines += ['', '## Detalle', '']
    for direction, r in report['direcciones'].items():
        lines += [f'### {direction}', '',
                  f"- Histograma de anticipación (n={r['anticipacion']['n']}): {r['anticipacion']['histograma']}",
                  f"- Criterio del cambio material: {r['criterio']}",
                  f"- Señales en la detección: {r['senales']}",
                  f"- Episodios con escalada: {r['con_escalada']} · duración mediana detección→cierre: {r['duracion_mediana_meses']} meses · cierre: {r['motivo_cierre']}", '']
    lines += ['## Lectura', '',
              'La mayoría de los cambios materiales se confirman en el mes anterior al aviso o el mismo mes. Es esperable por construcción:',
              'el monitor exige 3 meses de momentum y el cambio material 2 meses consecutivos desde el inicio estimado, y ambos leen la misma',
              '`base_health`. La anticipación mínima posible con este criterio es −1. Este criterio mide la **consistencia** del aviso con un cambio',
              'de tamaño material, no cuánto se adelanta a un evento externo. Para medir anticipación real hace falta un evento independiente:',
              'la caja-oráculo de los escenarios sintéticos o la perspectiva a 6 meses (punto hueco), pendientes de la siguiente entrega.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=ROOT / 'algorythm' / 'engine_results')
    args = parser.parse_args()
    data = json.loads((args.results / 'episodes.json').read_text())
    report = summarize(data)
    (args.results / 'episodes_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    (args.results / 'episodes_report.md').write_text(markdown(report, data.get('as_of')))
    print(json.dumps({k: v for k, v in report.items() if k != 'direcciones'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
