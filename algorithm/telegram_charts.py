import io
from pathlib import Path
from typing import Optional, Union

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
PANELS_PATH = HERE / 'engine_results' / 'score_panels.npz'


def generate_company_chart(
    company_id: str,
    panels_path: Optional[Union[str, Path]] = None,
    theme: str = 'telegram',
) -> bytes:
    """
    Renders a 24-month financial health trajectory chart for a given company.

    theme='telegram' is the original corporate navy/teal look used by the bot and
    the backend PNG endpoint. theme='embat' mirrors the front's Trayectoria chart
    (front/components/charts.tsx): black background, purple line, quiet grid.
    
    Styling:
    - Corporate dark mode (#050B2C background, #081138 plot area)
    - X-Ray score line in vibrant teal (#00A896) with soft fill under curve
    - Base solvency threshold at 60.0 (#FFD166 dashed line)
    - Prominent status indicator at latest cut (Red for DETERIORO, Yellow for TORCIENDOSE, Green for Solvente)
    
    Returns:
        PNG image bytes in memory (io.BytesIO).
    """
    DB_PATH = HERE.parent / 'xray.duckdb'
    cid = str(company_id).strip().upper()
    if cid.startswith("COMP_") and cid[5:].isdigit():
        cid = f"COMP_{cid[5:].zfill(4)}"
    elif cid.startswith("COMP") and cid[4:].isdigit():
        cid = f"COMP_{cid[4:].zfill(4)}"
    elif cid.isdigit():
        cid = f"COMP_{cid.zfill(4)}"

    loaded_from_db = False
    if not panels_path and DB_PATH.exists():
        try:
            import duckdb
            con = duckdb.connect(str(DB_PATH), read_only=True)
            rows = con.execute("""
                SELECT as_of, score, state, group_id 
                FROM company_scores 
                WHERE company_id = ? 
                ORDER BY as_of ASC;
            """, (cid,)).fetchall()
            con.close()
            if rows:
                scores = np.asarray([r[1] for r in rows], dtype=float)
                as_of_raw = [str(r[0]) for r in rows]
                states = [str(r[2]) for r in rows]
                group_id = str(rows[0][3]) if rows[0][3] else 'N/D'
                loaded_from_db = True
            else:
                con = duckdb.connect(str(DB_PATH), read_only=True)
                exists = con.execute("SELECT 1 FROM companies WHERE company_id = ?", (cid,)).fetchone()
                con.close()
                if not exists:
                    raise ValueError(f"Company {cid} not found in score panels catalogue")
        except ValueError:
            raise
        except Exception:
            pass

    if not loaded_from_db:
        target_path = Path(panels_path) if panels_path else PANELS_PATH
        if not target_path.exists():
            raise FileNotFoundError(f"Score panels file not found at {target_path}")

        with np.load(target_path, allow_pickle=False) as data:
            cids = [str(c) for c in data['company_id']]
            if cid not in cids:
                raise ValueError(f"Company {cid} not found in score panels catalogue")

            idx = cids.index(cid)
            scores = np.asarray(data['score'][idx], dtype=float)
            as_of_raw = [str(d) for d in data['as_of']]
            states = [str(s) for s in data['state'][idx]]
            group_id = str(data['group_id'][idx]) if 'group_id' in data else 'N/D'

    latest_score = float(scores[-1])
    latest_state = states[-1]
    latest_date = as_of_raw[-1]
    first_score = float(scores[0])
    delta_total = latest_score - first_score

    # Format x-axis dates: '2024-10-01' -> '10/24'
    labels = []
    for d in as_of_raw:
        parts = d.split('-')
        if len(parts) >= 2:
            labels.append(f"{parts[1]}/{parts[0][2:]}")
        else:
            labels.append(d)

    if theme == 'embat':
        return _draw_embat(scores, as_of_raw, latest_state)

    # Matplotlib styling
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 5), dpi=160)
    try:
        fig.patch.set_facecolor('#050B2C')
        ax.set_facecolor('#081138')

        # Main score curve
        line_color = '#00A896'
        marker_color = '#00E5C8'
        ax.plot(
            labels, scores,
            color=line_color,
            linewidth=2.6,
            marker='o',
            markersize=4.5,
            markerfacecolor=marker_color,
            markeredgecolor='#050B2C',
            markeredgewidth=1.0,
            label='Score X-Ray (0-100)',
            zorder=3
        )

        # Shaded area under the curve
        ax.fill_between(
            labels, scores,
            color=line_color,
            alpha=0.18,
            zorder=2
        )

        # Base solvency boundary at 60.0
        ax.axhline(
            60.0,
            color='#FFD166',
            linestyle='--',
            linewidth=1.6,
            alpha=0.85,
            label='Umbral Solvencia Base (60.0)',
            zorder=2
        )

        # Terminal point coloring based on health state
        if latest_state == 'DETERIORO':
            status_color = '#EF476F'  # Crimson Red
            status_label = '[DETERIORO CRITICO]'
        elif latest_state == 'TORCIENDOSE':
            status_color = '#FFD166'  # Amber Yellow
            status_label = '[TRAYECTORIA DESCENDENTE]'
        elif latest_state in ('RECUPERACION', 'MEJORANDO'):
            status_color = '#06D6A0'  # Emerald Green
            status_label = f'[{latest_state}]'
        elif latest_state == 'BACHE':
            status_color = '#118AB2'  # Cyan Blue
            status_label = '[BACHE TRANSITORIO]'
        else:
            status_color = '#06D6A0' if latest_score >= 60.0 else '#FFD166'
            status_label = f'[{latest_state}]'

        # Terminal point marker
        ax.plot(
            labels[-1], latest_score,
            marker='o',
            markersize=9.5,
            color=status_color,
            markeredgecolor='white',
            markeredgewidth=1.8,
            zorder=5
        )

        # Annotation callout on latest score
        delta_sign = '+' if delta_total > 0 else ''
        ax.annotate(
            f"{latest_score:.1f} pts ({latest_state})",
            xy=(labels[-1], latest_score),
            xytext=(-20, 14 if latest_score < 80 else -20),
            textcoords='offset points',
            color='white',
            fontsize=8.5,
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=status_color, edgecolor='none', alpha=0.9),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.1', color='white', lw=1.0),
            zorder=6
        )

        # Axes titles and labels
        ax.set_title(
            f"Trayectoria Score X-Ray · {cid} ({group_id})\n"
            f"Corte: {latest_date} | Estado: {status_label} | Score: {latest_score:.2f} / 100",
            color='white',
            fontsize=11.5,
            fontweight='bold',
            pad=12,
            loc='left'
        )
        ax.set_ylabel('Score Financiero (0 - 100)', color='#A0AEC0', fontsize=9.5, labelpad=8)
        ax.set_ylim(0, 100)

        # Ticks and Grid
        ax.tick_params(colors='#A0AEC0', labelsize=8)
        plt.xticks(rotation=45, ha='right')
        ax.grid(True, linestyle=':', alpha=0.18, color='#A0AEC0')

        # Spines border styling
        for spine in ax.spines.values():
            spine.set_edgecolor('#1E2958')
            spine.set_linewidth(1.2)

        # Legend
        ax.legend(
            facecolor='#050B2C',
            edgecolor='#1E2958',
            labelcolor='white',
            loc='lower left',
            fontsize=8.5,
            framealpha=0.9
        )

        plt.tight_layout()

        # Save to memory buffer
        buffer = io.BytesIO()
        plt.savefig(
            buffer,
            format='png',
            facecolor=fig.get_facecolor(),
            edgecolor='none',
            bbox_inches='tight'
        )
        buffer.seek(0)
        return buffer.getvalue()
    finally:
        plt.close(fig)


# ── Tema Embat: el mismo dibujo que front/components/charts.tsx (Trayectoria) ──
EMBAT_BG = '#131218'            # superficie de tarjeta sobre --color-deep
EMBAT_LINE = '#b083e8'          # --color-purple
EMBAT_INK_3 = '#afafbb'         # eje
EMBAT_ESTADO = {
    'DETERIORO': '#e5775b', 'TORCIENDOSE': '#e59f5e', 'BACHE': '#dfb631',
    'ESTABLE': '#9fe3b4', 'MEJORANDO': '#80efa2', 'RECUPERACION': '#80efa2',
}
MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def _mes_corto(iso: str) -> str:
    parts = iso.split('-')
    if len(parts) < 2 or not parts[1].isdigit():
        return iso
    return f"{MESES[int(parts[1]) - 1]} {parts[0][2:]}"


def _draw_embat(scores, as_of_raw, latest_state) -> bytes:
    x = np.arange(len(scores))
    fig, ax = plt.subplots(figsize=(6.7, 3.0), dpi=160)
    try:
        fig.patch.set_facecolor(EMBAT_BG)
        ax.set_facecolor(EMBAT_BG)
        ax.fill_between(x, scores, 0, color=EMBAT_LINE, alpha=0.16, linewidth=0, zorder=2)
        ax.plot(x, scores, color=EMBAT_LINE, linewidth=2.2, solid_capstyle='round', zorder=3)
        ax.axhline(60.0, color='white', alpha=0.14, linestyle=(0, (3, 3)), linewidth=1.0, zorder=2)
        color = EMBAT_ESTADO.get(latest_state, '#afafbb')
        ax.plot(x[-1], scores[-1], marker='o', markersize=8.5, color=color,
                markeredgecolor='#0a0810', markeredgewidth=2, zorder=5)
        ax.annotate(f"{scores[-1]:.1f}".replace('.', ','), xy=(x[-1], scores[-1]),
                    xytext=(0, 12 if scores[-1] < 85 else -18), textcoords='offset points',
                    ha='center', color=color, fontsize=12, fontweight='bold', zorder=6)
        ax.set_xlim(-0.5, len(scores) - 0.5)
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_xticks(x[::3])
        ax.set_xticklabels([_mes_corto(as_of_raw[i]) for i in x[::3]])
        ax.tick_params(colors=EMBAT_INK_3, labelsize=11, length=0, pad=6)
        ax.grid(True, axis='y', color='white', alpha=0.07, linewidth=1)
        ax.grid(False, axis='x')
        for side, spine in ax.spines.items():
            spine.set_visible(side == 'bottom')
            spine.set_edgecolor('white')
            spine.set_alpha(0.12)
        plt.tight_layout(pad=0.6)
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', facecolor=EMBAT_BG, edgecolor='none')
        return buffer.getvalue()
    finally:
        plt.close(fig)
