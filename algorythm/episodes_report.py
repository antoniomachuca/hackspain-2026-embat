"""Medición básica de episodios: anticipación, avisos tardíos, no confirmados y pendientes.

Run: python -m algorythm.episodes_report
Calcula sobre score_panels.npz + bank_inputs.npz (el mismo recorte que el API).
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from algorythm.bank_panels import SCORE_FIELDS, load_bank_inputs
from algorythm.levers_objects import OBJECTS_PATH, ap_pending_vector
from algorythm.score_episodes import build_episodes, month_diff

ROOT = Path(__file__).resolve().parents[1]


def summarize(data):
    episodes = [e for c in data['companies'].values() for e in c['episodios']]
    report = {'empresas': len(data['companies']),
              'empresas_con_episodio': sum(1 for c in data['companies'].values() if c['episodios']),
              'episodios': len(episodes), 'direcciones': {}}
    for direction in ('deterioro', 'mejora'):
        rows = [e for e in episodes if e['direccion'] == direction]
        lead = np.array([e['meses_anticipacion'] for e in rows if e['meses_anticipacion'] is not None])
        hueco = np.array([e['perspectiva']['meses_antes_deteccion']
                          for e in rows if e.get('perspectiva')])
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
            'perspectiva': {'n': int(len(hueco)),
                            'mediana_meses_antes': float(np.median(hueco)) if len(hueco) else None},
            'con_escalada': sum(1 for e in rows if e['escaladas']),
            'senales': dict(Counter(s['senal'] for e in rows for s in e['senales'])),
            'duracion_mediana_meses': float(np.median(durations)) if durations else None,
            'motivo_cierre': dict(Counter(e['motivo_cierre'] for e in rows if e['cierre'])),
        }
    return report


def markdown(report, as_of):
    lines = [f'# Medición de episodios · corte {as_of}', '',
             f"{report['empresas']} empresas, {report['empresas_con_episodio']} con al menos un episodio, {report['episodios']} episodios.", '',
             'Anticipación material = cambio material − detección (meses), JSON de medición.',
             'El N visible en ficha es perspectiva.meses_antes_deteccion (hueco → rojo).', '',
             '| Dirección | Episodios | Confirmados | No confirmados | Pendientes | Anticipación mediana | Aviso antes | Mismo mes | Aviso tardío | Hueco n |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for direction, r in report['direcciones'].items():
        c, a, p = r['confirmacion'], r['anticipacion'], r['perspectiva']
        pct = lambda v: '—' if v is None else f'{v:.0%}'
        lines.append(f"| {direction} | {r['episodios']} | {c.get('confirmado', 0)} | {c.get('no_confirmado', 0)} | {c.get('pendiente', 0)} | "
                     f"{a['mediana'] if a['mediana'] is not None else '—'} | {pct(a['aviso_antes'])} | {pct(a['mismo_mes'])} | {pct(a['aviso_tardio'])} | {p['n']} |")
    lines += ['', '## Detalle', '']
    for direction, r in report['direcciones'].items():
        lines += [f'### {direction}', '',
                  f"- Histograma de anticipación (n={r['anticipacion']['n']}): {r['anticipacion']['histograma']}",
                  f"- Criterio del cambio material: {r['criterio']}",
                  f"- Señales en la detección: {r['senales']}",
                  f"- Perspectiva asociada: n={r['perspectiva']['n']}, mediana meses antes={r['perspectiva']['mediana_meses_antes']}",
                  f"- Episodios con escalada: {r['con_escalada']} · duración mediana detección→cierre: {r['duracion_mediana_meses']} meses · cierre: {r['motivo_cierre']}", '']
    lines += ['## Lectura', '',
              'La mayoría de los cambios materiales se confirman en el mes anterior al aviso o el mismo mes. Es esperable por construcción:',
              'el monitor exige 3 meses de momentum y el cambio material 2 meses consecutivos desde el inicio estimado, y ambos leen la misma',
              '`base_health`. La anticipación mínima posible con este criterio es −1. Este criterio mide la **consistencia** del aviso con un cambio',
              'de tamaño material, no cuánto se adelanta a un evento externo. La anticipación real es el punto hueco (perspectiva a 6 meses).', '']
    return '\n'.join(lines)


def load_snapshot(directory):
    directory = Path(directory)
    with np.load(directory / 'score_panels.npz', allow_pickle=False) as stored:
        panels = {key: stored[key] for key in stored.files}
    bank = None
    bank_path = directory / 'bank_inputs.npz'
    if bank_path.exists():
        raw = load_bank_inputs(bank_path)
        bank = {key: raw[key] for key in SCORE_FIELDS if key in raw}
    ap = ap_pending_vector(panels['company_id']) if OBJECTS_PATH.exists() else None
    companies = build_episodes(panels, bank=bank, ap_pending=ap)
    as_of = str(panels['as_of'][-1]) if len(panels.get('as_of', [])) else None
    return {'as_of': as_of, 'companies': companies}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=ROOT / 'algorythm' / 'engine_results')
    args = parser.parse_args()
    data = load_snapshot(args.results)
    report = summarize(data)
    (args.results / 'episodes_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    (args.results / 'episodes_report.md').write_text(markdown(report, data.get('as_of')))
    print(json.dumps({k: report[k] for k in ('empresas', 'empresas_con_episodio', 'episodios')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
