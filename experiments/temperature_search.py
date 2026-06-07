"""
EXPERIMENTO DE TEMPERATURA

Busca la combinación de temperaturas de los agentes que logra el MAYOR overlap
(consistencia entre corridas) SIN SACRIFICAR la creatividad.

¿Por qué no basta con bajar todo a 0? Porque a temperatura 0 el sistema se vuelve un
robot: copia mecánicamente el ranking de Sharpe del agente Quant y deja de ejercer
criterio (diversificación sectorial, juicio cualitativo). Queremos algo repetible pero
que aún piense.

Por eso medimos DOS cosas por cada combinación de temperaturas:

  • CONSISTENCIA  = acciones en común, en promedio, entre dos corridas (de N).
                    Más alto = más repetible.  (lo que llamamos "overlap")

  • CREATIVIDAD   = qué fracción de la cartera se aparta del ranking ingenuo
                    "top-N por Sharpe". Más alto = el equipo ejerce más criterio
                    propio en vez de copiar la métrica. Independiente de la
                    consistencia: se puede ser repetible Y creativo a la vez.

Recomendamos la combinación con MAYOR consistencia cuya creatividad siga por encima de
un piso mínimo (configurable con --creativity-floor).

Uso:
    python experiments/temperature_search.py                  # todos los perfiles, 3 corridas c/u
    python experiments/temperature_search.py --runs 2         # más barato
    python experiments/temperature_search.py --only frio,medio
    python experiments/temperature_search.py --creativity-floor 0.3

Ojo: esto corre el pipeline (perfiles × corridas) veces, con llamadas reales al LLM.
Cuesta tiempo y tokens. Empieza con pocos perfiles y pocas corridas.
"""

import argparse
import itertools
import json
import sys
from datetime import datetime
from pathlib import Path

# Permite ejecutar este script directamente (agrega la raíz del repo al path).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402

from src.config import OUTPUT_DIR, load_config  # noqa: E402
from src.orchestrator import run_pipeline  # noqa: E402
from src.tools import compute_metrics  # noqa: E402

console = Console()

# Combinaciones de temperaturas a probar, de más "fría" a más "caliente".
# Cada perfil asigna una temperatura por agente. Edita libremente: agrega, quita o
# cambia perfiles para explorar otras combinaciones.
PROFILES = {
    "frio":        {"research": 0.0, "quant": 0.0, "risk": 0.0, "portfolio_manager": 0.0},
    "bajo":        {"research": 0.2, "quant": 0.0, "risk": 0.1, "portfolio_manager": 0.2},
    "medio":       {"research": 0.4, "quant": 0.1, "risk": 0.2, "portfolio_manager": 0.3},
    "alto":        {"research": 0.7, "quant": 0.2, "risk": 0.3, "portfolio_manager": 0.6},
    "caotico":     {"research": 1.0, "quant": 0.5, "risk": 0.5, "portfolio_manager": 1.0},
}


def average_pairwise_overlap(ticker_sets):
    """Promedio de acciones en común entre todos los pares de carteras."""
    pairs = list(itertools.combinations(ticker_sets, 2))
    if not pairs:
        return float("nan")
    return sum(len(a & b) for a, b in pairs) / len(pairs)


def naive_top_sharpe(size, period):
    """
    Cartera "ingenua" de referencia: las `size` acciones del universo con mayor Sharpe.
    No usa el LLM — es puro ranking cuantitativo. Sirve para medir creatividad: cuánto
    se aparta de esto la cartera real.
    """
    universe = load_config()["universe"]["tickers"]
    metrics = json.loads(compute_metrics(universe, period))
    ranked = sorted(
        (t for t, m in metrics.items() if "sharpe_ratio" in m),
        key=lambda t: metrics[t]["sharpe_ratio"],
        reverse=True,
    )
    return set(ranked[:size])


def main():
    parser = argparse.ArgumentParser(description="Busca la mejor combinación de temperaturas.")
    parser.add_argument("--runs", type=int, default=3, help="Corridas por perfil (default 3).")
    parser.add_argument("--only", type=str, default="", help="Perfiles a probar, separados por coma.")
    parser.add_argument("--creativity-floor", type=float, default=0.2,
                        help="Creatividad mínima aceptable (0-1, default 0.2).")
    args = parser.parse_args()

    config = load_config()
    size = config["portfolio"]["size"]
    period = config["portfolio"]["lookback_period"]

    selected = [p.strip() for p in args.only.split(",") if p.strip()] or list(PROFILES)
    profiles = {name: PROFILES[name] for name in selected if name in PROFILES}
    if not profiles:
        console.print(f"[red]No hay perfiles válidos. Disponibles: {', '.join(PROFILES)}[/]")
        return

    total_runs = len(profiles) * args.runs
    console.print(
        Panel(
            f"Voy a probar [bold]{len(profiles)} combinaciones[/] de temperatura, "
            f"[bold]{args.runs} corridas[/] cada una ([bold]{total_runs} corridas[/] en total).\n"
            f"Mido consistencia (overlap) y creatividad (apartarse del top-{size} por Sharpe).\n"
            f"Piso de creatividad aceptable: {args.creativity_floor:.0%}.",
            title="🌡️  Experimento de Temperatura",
            border_style="bold cyan",
        )
    )

    console.print("\n[dim]Calculando la cartera ingenua de referencia (top-Sharpe)...[/]")
    baseline = naive_top_sharpe(size, period)
    console.print(f"[dim]Referencia top-{size} por Sharpe: {', '.join(sorted(baseline))}[/]")

    results = []
    for name, temps in profiles.items():
        temps_str = " · ".join(f"{k[:2].capitalize()}{v}" for k, v in temps.items())
        console.print(f"\n[bold cyan]▶ Perfil '{name}'[/]  ({temps_str})")
        ticker_sets = []
        for i in range(1, args.runs + 1):
            result = run_pipeline(verbose=False, temperatures=temps)
            tickers = set(result["tickers"])
            ticker_sets.append(tickers)
            console.print(f"  Corrida {i}: {', '.join(sorted(tickers))}")

        consistency = average_pairwise_overlap(ticker_sets)
        # Creatividad: fracción promedio de la cartera que NO está en el top-Sharpe.
        creativity = sum(len(s - baseline) / size for s in ticker_sets) / len(ticker_sets)
        results.append({
            "name": name, "temps": temps, "temps_str": temps_str,
            "consistency": consistency, "creativity": creativity,
        })

    # ── Recomendación ───────────────────────────────────────────────────
    eligible = [r for r in results if r["creativity"] >= args.creativity_floor]
    pool = eligible or results
    best = max(pool, key=lambda r: (r["consistency"], r["creativity"]))

    table = Table(title="Combinaciones de temperatura: consistencia vs creatividad")
    table.add_column("Perfil", style="bold")
    table.add_column("Temperaturas")
    table.add_column(f"Consistencia (de {size})", justify="center")
    table.add_column("Creatividad", justify="center")
    table.add_column("", justify="center")
    for r in sorted(results, key=lambda r: r["consistency"], reverse=True):
        cons = f"{r['consistency']:.1f}"
        crea = f"{r['creativity'] * 100:.0f}%"
        flags = []
        if r["creativity"] < args.creativity_floor:
            crea = f"[red]{crea}[/]"
            flags.append("[red]rígido[/]")
        if r["name"] == best["name"]:
            flags.append("[green]⭐ recomendado[/]")
        table.add_row(r["name"], r["temps_str"], cons, crea, "  ".join(flags))
    console.print("\n")
    console.print(table)

    rec = (
        f"[bold]Mejor combinación: '{best['name']}'[/]  ({best['temps_str']})\n\n"
        f"Logra la mayor consistencia ([bold]{best['consistency']:.1f} de {size}[/]) "
        f"manteniendo la creatividad en [bold]{best['creativity'] * 100:.0f}%[/] "
        f"(≥ piso de {args.creativity_floor:.0%}).\n\n"
        f"[dim]Aplica estas temperaturas editando el campo `temperature` en cada "
        f"archivo de agents/ para fijar esta combinación como la oficial.[/]"
    )
    if not eligible:
        rec = (
            f"[yellow]Ningún perfil alcanzó el piso de creatividad "
            f"({args.creativity_floor:.0%}).[/] El sistema tiende a copiar el ranking "
            f"de Sharpe. Gana por consistencia: [bold]'{best['name']}'[/].\n\n"
            f"Sugerencia: sube un poco las temperaturas o enriquece los prompts de los "
            f"agentes para incentivar más criterio propio."
        )
    console.print(Panel(rec, title="📊 Recomendación", border_style="bold green"))

    _save_summary(results, best, baseline, size, args)


def _save_summary(results, best, baseline, size, args):
    """Guarda el resultado del experimento en output/."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"temperatura_{stamp}.md"

    lines = [
        f"# Experimento de temperatura — {stamp}",
        "",
        f"- **Corridas por perfil:** {args.runs}",
        f"- **Piso de creatividad:** {args.creativity_floor:.0%}",
        f"- **Referencia top-{size} por Sharpe:** {', '.join(sorted(baseline))}",
        f"- **Recomendado:** `{best['name']}` ({best['temps_str']})",
        "",
        f"| Perfil | Temperaturas | Consistencia (de {size}) | Creatividad |",
        "|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda r: r["consistency"], reverse=True):
        lines.append(
            f"| {r['name']} | {r['temps_str']} | {r['consistency']:.1f} | "
            f"{r['creativity'] * 100:.0f}% |"
        )
    lines += [
        "",
        "**Consistencia** = acciones en común, en promedio, entre dos corridas.",
        "**Creatividad** = fracción de la cartera que se aparta del ranking ingenuo "
        "top-Sharpe (más alto = más criterio propio).",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"\n[bold green]✓ Resumen guardado en:[/] {path}")


if __name__ == "__main__":
    main()
