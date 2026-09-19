import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PANELS_PATH = HERE / 'engine_results' / 'score_panels.npz'
BALANCES_PATH = ROOT / 'dataset' / 'balances.csv'

DB_PATH = ROOT / 'xray.duckdb'

# In-memory cache for fast repeated queries
_CACHED_PANELS: Optional[Dict[str, np.ndarray]] = None
_CACHED_BALANCES: Optional[Dict[str, float]] = None


def load_panels(panels_path: Optional[Path] = None) -> Optional[Dict[str, np.ndarray]]:
    """Loads and caches score_panels.npz."""
    global _CACHED_PANELS
    target = Path(panels_path) if panels_path else PANELS_PATH
    if not target.exists():
        return None
    if _CACHED_PANELS is not None and not panels_path:
        return _CACHED_PANELS
    with np.load(target, allow_pickle=False) as data:
        loaded = {k: data[k] for k in data.files}
        if not panels_path:
            _CACHED_PANELS = loaded
        return loaded


def load_balances(balances_path: Optional[Path] = None) -> Dict[str, float]:
    """Loads and caches sum of balances per company from DuckDB (or dataset/balances.csv fallback)."""
    global _CACHED_BALANCES
    if _CACHED_BALANCES is not None and not balances_path:
        return _CACHED_BALANCES

    # 1. Intentar primero DuckDB (fuente centralizada)
    if not balances_path and DB_PATH.exists():
        try:
            import duckdb
            con = duckdb.connect(str(DB_PATH), read_only=True)
            rows = con.execute("SELECT company_id, COALESCE(SUM(balance), 0.0) FROM balances GROUP BY company_id;").fetchall()
            con.close()
            balances = {r[0]: float(r[1]) for r in rows}
            _CACHED_BALANCES = balances
            return balances
        except Exception:
            pass

    # 2. Fallback a dataset/balances.csv
    target = Path(balances_path) if balances_path else BALANCES_PATH
    if not target.exists():
        return {}
    balances: Dict[str, float] = {}
    try:
        with target.open(newline='', encoding='utf-8') as source:
            reader = csv.DictReader(source)
            for row in reader:
                cid = row.get('company_id')
                if not cid:
                    continue
                try:
                    val = float(row.get('balance') or 0.0)
                except ValueError:
                    val = 0.0
                balances[cid] = balances.get(cid, 0.0) + val
    except Exception:
        pass
    if not balances_path:
        _CACHED_BALANCES = balances
    return balances


def get_company_data(company_id: str, panels_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Extracts the financial cut and historical points for a given company (DuckDB primary, NPZ fallback)."""
    cid_upper = company_id.strip().upper()
    if not cid_upper.startswith("COMP_") and cid_upper.startswith("COMP") and cid_upper[4:].isdigit():
        cid_upper = f"COMP_{cid_upper[4:]}"
    elif cid_upper.isdigit():
        cid_upper = f"COMP_{cid_upper.zfill(4)}"

    # 1. Intentar primero DuckDB (fuente centralizada)
    if not panels_path and DB_PATH.exists():
        try:
            import duckdb
            con = duckdb.connect(str(DB_PATH), read_only=True)
            rows = con.execute("""
                SELECT 
                    as_of, score, state, momentum, base_health,
                    liquidity_points, collections_points, debt_points,
                    momentum_points, growth_points, fragility_points,
                    fragility, clipping_points, group_id
                FROM company_scores 
                WHERE company_id = ? 
                ORDER BY as_of ASC;
            """, (cid_upper,)).fetchall()
            con.close()
            if rows:
                last_row = rows[-1]
                base_idx = max(0, len(rows) - 4)  # 3 meses antes
                base_row = rows[base_idx]
                return {
                    'index': 0,
                    'company_id': cid_upper,
                    'group_id': str(last_row[13]),
                    'as_of': str(last_row[0]),
                    'comparison_as_of': str(base_row[0]),
                    'current_score': float(last_row[1]),
                    'current_state': str(last_row[2]),
                    'momentum': float(last_row[3]),
                    'base_health': float(last_row[4]),
                    'liquidity_points': float(last_row[5]),
                    'collections_points': float(last_row[6]),
                    'debt_points': float(last_row[7]),
                    'momentum_points': float(last_row[8]),
                    'growth_points': float(last_row[9]),
                    'fragility_points': float(last_row[10]),
                    'fragility': float(last_row[11]),
                    'clipping_points': float(last_row[12]),
                    'historical_scores': [float(r[1]) for r in rows],
                    'as_of_dates': [str(r[0]) for r in rows]
                }
        except Exception:
            pass

    # 2. Fallback a score_panels.npz
    panels = load_panels(panels_path)
    if not panels:
        return None
    cids = [str(c) for c in panels['company_id']]
    if cid_upper not in cids:
        return None
    idx = cids.index(cid_upper)
    last_idx = panels['score'].shape[1] - 1
    base_idx = max(0, last_idx - 3)

    return {
        'index': idx,
        'company_id': cid_upper,
        'group_id': str(panels['group_id'][idx]),
        'as_of': str(panels['as_of'][last_idx]),
        'comparison_as_of': str(panels['as_of'][base_idx]),
        'current_score': float(panels['score'][idx, last_idx]),
        'current_state': str(panels['state'][idx, last_idx]),
        'momentum': float(panels['momentum'][idx, last_idx]),
        'base_health': float(panels['base_health'][idx, last_idx]),
        'liquidity_points': float(panels['liquidity_points'][idx, last_idx]),
        'collections_points': float(panels['collections_points'][idx, last_idx]),
        'debt_points': float(panels['debt_points'][idx, last_idx]),
        'momentum_points': float(panels['momentum_points'][idx, last_idx]),
        'growth_points': float(panels['growth_points'][idx, last_idx]),
        'fragility_points': float(panels['fragility_points'][idx, last_idx]),
        'fragility': float(panels['fragility'][idx, last_idx]),
        'clipping_points': float(panels['clipping_points'][idx, last_idx]),
        'historical_scores': panels['score'][idx, :].tolist(),
        'as_of_dates': [str(d) for d in panels['as_of']]
    }


def calculate_projection(
    amount: float,
    current_score: float,
    liquidity_points: float,
    collections_points: float,
    fragility_points: float,
    fragility: float,
    reference_scale: float
) -> Tuple[float, float, float, float, float]:
    """
    Simulates the counterfactual impact of an injection amount.
    Returns: (delta_score, projected_score, l_gain, f_gain, c_gain)
    """
    scale = max(25000.0, reference_scale)
    r = max(0.0, amount) / scale

    # 1. Operational liquidity coverage gain (headroom up to 50 pts)
    l_headroom = max(0.0, 50.0 - liquidity_points)
    l_gain = l_headroom * (r / (r + 1.0)) * 0.90

    # 2. Stress & fragility reduction (recovering up to 8 negative points)
    # Fragility penalty is F_points = -8 * fragility
    f_projected = fragility / (1.0 + 2.0 * r)
    f_gain = max(0.0, (-8.0 * f_projected) - fragility_points)

    # 3. Factoring / ERP collections acceleration (converting pending invoices)
    c_headroom = max(0.0, 30.0 - collections_points)
    c_gain = c_headroom * 0.20 * (r / (r + 1.0))

    raw_delta = l_gain + f_gain + c_gain
    projected_score = min(100.0, max(0.0, current_score + raw_delta))
    delta_score = projected_score - current_score
    return delta_score, projected_score, l_gain, f_gain, c_gain


def solve_optimal_injection(
    current_score: float,
    liquidity_points: float,
    collections_points: float,
    fragility_points: float,
    fragility: float,
    reference_scale: float,
    target_score: float = 60.0
) -> float:
    """
    Calculates the minimal injection amount required to reach target_score (60.0 or 55.0).
    Uses bisection search over the monotonic projection function.
    """
    if current_score >= target_score:
        return 25000.0  # Proactive maintenance tranche

    scale = max(25000.0, reference_scale)
    # Check max attainable score
    _, max_proj, _, _, _ = calculate_projection(
        scale * 100.0, current_score, liquidity_points, collections_points,
        fragility_points, fragility, scale
    )
    effective_target = min(target_score, max_proj - 0.1) if max_proj < target_score else target_score
    if effective_target <= current_score:
        return 25000.0

    low = 1000.0
    high = scale * 50.0
    for _ in range(25):
        mid = (low + high) / 2.0
        _, proj, _, _, _ = calculate_projection(
            mid, current_score, liquidity_points, collections_points,
            fragility_points, fragility, scale
        )
        if proj < effective_target:
            low = mid
        else:
            high = mid

    # Round up to clean corporate tranche (nearest 5,000 €)
    rounded = math.ceil(high / 5000.0) * 5000.0
    return max(5000.0, float(rounded))


def determine_projected_state(current_state: str, current_score: float, projected_score: float, delta_score: float) -> str:
    """
    Determines if the counterfactual injection rescues the company from DETERIORO/TORCIENDOSE.
    """
    if projected_score >= 60.0:
        if current_state in ('DETERIORO', 'TORCIENDOSE', 'BACHE'):
            return 'RECUPERACION' if (current_state == 'DETERIORO' or delta_score >= 8.0) else 'ESTABLE'
        return 'ESTABLE' if current_state == 'ESTABLE' else 'MEJORANDO'
    elif projected_score >= 50.0:
        return 'ESTABLE'
    elif projected_score >= 40.0:
        return 'TORCIENDOSE' if current_state == 'DETERIORO' else current_state
    else:
        return current_state


def select_recommended_product(liquidity_points: float, fragility_points: float, collections_points: float) -> Tuple[str, str]:
    """
    Selects the Embat financial solution tailored to the primary bottleneck.
    """
    if liquidity_points < 25.0:
        return (
            "Línea de Factoring y Anticipo de Facturas con Embat",
            "Permite monetizar las cuentas a cobrar de inmediato sin computar endeudamiento bancario adicional (CIRBE), restaurando la cobertura de circulante a 30 días."
        )
    elif abs(fragility_points) > 3.0:
        return (
            "Línea de Crédito Revolving de Tesorería Embat",
            "Elimina tensiones de liquidez intradía y descubiertos temporales, neutralizando de raíz la penalización por estrés financiero y volatilidad."
        )
    else:
        return (
            "Anticipo Dinámico de Cobros y Conciliación ERP",
            "Acelera el período medio de cobro (DSO) integrando el ERP directamente con las entidades pagadoras, afianzando un score bancario preferente."
        )


def simulate_whatif(
    company_id: str,
    injection_amount: Optional[float] = None,
    panels_path: Optional[Path] = None,
    balances_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Main counterfactual simulation engine.
    
    Models the impact of a liquidity injection or invoice advance on:
    - Operational liquidity coverage ratio (+L)
    - Financial stress and fragility reduction (-Fragility)
    - Additive projected score recalculation (+Delta Score)
    - State transition check (rescuing DETERIORO -> ESTABLE / RECUPERACION)
    - Automatically calculates optimal minimum injection if amount is None.
    - Generates executive message for CFO.
    """
    comp = get_company_data(company_id, panels_path)
    if not comp:
        return None

    balances = load_balances(balances_path)
    raw_balance = balances.get(comp['company_id'], 0.0)
    ref_scale = abs(raw_balance) if abs(raw_balance) >= 20000.0 else 50000.0

    is_optimal_computed = False
    if injection_amount is None or injection_amount <= 0:
        amount = solve_optimal_injection(
            comp['current_score'],
            comp['liquidity_points'],
            comp['collections_points'],
            comp['fragility_points'],
            comp['fragility'],
            ref_scale,
            target_score=60.0
        )
        is_optimal_computed = True
    else:
        amount = float(injection_amount)

    delta_s, proj_score, l_gain, f_gain, c_gain = calculate_projection(
        amount,
        comp['current_score'],
        comp['liquidity_points'],
        comp['collections_points'],
        comp['fragility_points'],
        comp['fragility'],
        ref_scale
    )

    proj_state = determine_projected_state(
        comp['current_state'],
        comp['current_score'],
        proj_score,
        delta_s
    )

    product_name, product_rationale = select_recommended_product(
        comp['liquidity_points'],
        comp['fragility_points'],
        comp['collections_points']
    )

    # Executive message formatting
    amount_str = f"{amount:,.0f} €".replace(',', '.')
    state_tag = {
        'DETERIORO': '🚨 DETERIORO',
        'TORCIENDOSE': '⚠️ TORCIENDOSE',
        'ESTABLE': '🟡 ESTABLE',
        'RECUPERACION': '🟢 RECUPERACION',
        'MEJORANDO': '📈 MEJORANDO',
        'BACHE': '⏱ BACHE'
    }.get(comp['current_state'], comp['current_state'])

    proj_state_tag = {
        'ESTABLE': '🟢 ESTABLE (Solvencia Recuperada)',
        'RECUPERACION': '🟢 RECUPERACION (Rescate Confirmado)',
        'MEJORANDO': '📈 MEJORANDO (Trayectoria Positiva)',
        'TORCIENDOSE': '⚠️ TORCIENDOSE (Riesgo Mitigado)',
        'DETERIORO': '🚨 DETERIORO (Requiere Mayor Inyección)'
    }.get(proj_state, proj_state)

    opt_tag = " <i>(Inyección óptima mínima calculada para cruzar umbral)</i>" if is_optimal_computed else ""

    summary_html = (
        f"💡 <b>SIMULADOR CONTRAFACTUAL WHAT-IF · X-RAY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Sociedad:</b> <code>{comp['company_id']}</code> <i>({comp['group_id']})</i>\n"
        f"📅 <b>Corte actual:</b> <code>{comp['as_of']}</code>\n\n"
        f"🔍 <b>Diagnóstico Financiero de Partida:</b>\n"
        f"  • Score Actual: <b>{comp['current_score']:.2f} / 100</b>\n"
        f"  • Estado: <b>{state_tag}</b>\n"
        f"  • Cobertura de Liquidez: <code>{comp['liquidity_points']:.2f} / 50 pts</code>\n"
        f"  • Penalización por Estrés: <code>{comp['fragility_points']:.2f} pts</code>\n\n"
        f"💰 <b>Inyección / Anticipo Simulado:</b>\n"
        f"  • Importe: <b>{amount_str}</b>{opt_tag}\n\n"
        f"📈 <b>Impacto Cuantitativo Proyectado (Waterfall):</b>\n"
        f"  💧 Aporte Cobertura Operativa: <code>+{l_gain:.2f} pts</code>\n"
        f"  🛡 Alivio de Estrés Financiero: <code>+{f_gain:.2f} pts</code>\n"
        f"  📑 Aceleración Cobros ERP: <code>+{c_gain:.2f} pts</code>\n"
        f"  ─────────────────────────\n"
        f"  📊 <b>Nuevo Score Proyectado:</b> <b>{proj_score:.2f} / 100</b> (🔺 <b>+{delta_s:.2f} pts</b>)\n"
        f"  🚦 <b>Nuevo Estado:</b> <b>{proj_state_tag}</b>\n\n"
        f"💼 <b>Recomendación Ejecutiva para CFO:</b>\n"
        f"  👉 <b>Solución Embat:</b> <i>{product_name}</i>\n"
        f"  ℹ️ {product_rationale}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <i>Simulación contrafactual estricta basada en el motor X-Ray</i>"
    )

    return {
        'company_id': comp['company_id'],
        'group_id': comp['group_id'],
        'as_of': comp['as_of'],
        'current_score': comp['current_score'],
        'current_state': comp['current_state'],
        'injection_amount': amount,
        'is_optimal_computed': is_optimal_computed,
        'delta_score': delta_s,
        'projected_score': proj_score,
        'projected_state': proj_state,
        'liquidity_gain': l_gain,
        'fragility_gain': f_gain,
        'collections_gain': c_gain,
        'recommended_product': product_name,
        'product_rationale': product_rationale,
        'summary_html': summary_html
    }
