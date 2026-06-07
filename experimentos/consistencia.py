"""
EXPERIMENTO DE CONSISTENCIA

Demuestra el punto central del curso: cuando le pones PROCESO a la IA (roles con
criterios claros + datos reales), volver a correr el sistema produce carteras muy
parecidas — al contrario del prompt suelto, donde cada corrida daba algo distinto.

Corre el pipeline varias veces y mide cuántas acciones comparten, en promedio, dos
carteras cualesquiera (la misma métrica de la presentación: "acciones en común, de N").

Uso:
    python experimentos/consistencia.py            # 3 corridas
    python experimentos/consistencia.py --runs 5   # 5 corridas

Ojo: cada corrida hace llamadas reales al LLM (necesitas tu API key en .env) y cuesta
unos minutos. Empieza con pocas corridas.
"""

import argparse
import itertools
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Permite ejecutar este script directamente (agrega la raíz del repo al path).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402

from src.config import OUTPUT_DIR, load_config  # noqa: E402
from src.orchestrator import run_pipeline  # noqa: E402

console = Console()

# Referencias de la Clase 1 (prompt suelto), para contrastar.
BASELINE_PROMPT_SUELTO = 3.1   # dos equipos cualquiera, de 10
BASELINE_MISMO_MODELO = 4.3    # dos equipos con el mismo modelo, de 10


def average_pairwise_overlap(ticker_sets: list[set]) -> float:
    """Promedio de acciones en común entre todos los pares de carteras."""
    pairs = list(itertools.combinations(ticker_sets, 2))
    if not pairs:
        return float("nan")
    return sum(len(a & b) for a, b in pairs) / len(pairs)


def main():
    parser = argparse.ArgumentParser(description="Mide la consistencia de la cartera.")
    parser.add_argument("--runs", type=int, default=3, help="Número de corridas (default 3).")
    args = parser.parse_args()

    config = load_config()
    size = config["portfolio"]["size"]

    console.print(
        Panel(
            f"Voy a correr el sistema [bold]{args.runs} veces[/] y comparar las "
            f"carteras resultantes.\nObjetivo: ver cuántas de las {size} acciones se "
            f"repiten entre corridas.",
            title="🔁 Experimento de Consistencia",
            border_style="bold cyan",
        )
    )

    runs: list[list[str]] = []
    for i in range(1, args.runs + 1):
        console.print(f"\n[bold cyan]▶ Corrida {i}/{args.runs}[/] (esto toma un momento)...")
        result = run_pipeline(verbose=False)
        tickers = sorted(result["tickers"])
        runs.append(tickers)
        console.print(f"  Cartera {i}: [bold]{', '.join(tickers)}[/]  ({len(tickers)} acciones)")

    # ── Análisis ────────────────────────────────────────────────────────
    ticker_sets = [set(r) for r in runs]
    freq = Counter(t for s in ticker_sets for t in s)
    stable_core = sorted(t for t, c in freq.items() if c == args.runs)
    avg_overlap = average_pairwise_overlap(ticker_sets)

    console.print("\n")
    table = Table(title="¿En cuántas corridas apareció cada acción?")
    table.add_column("Ticker", style="bold")
    table.add_column(f"Apariciones (de {args.runs})", justify="center")
    table.add_column("¿Núcleo estable?", justify="center")
    for ticker, count in freq.most_common():
        nucleo = "✅" if count == args.runs else ""
        style = "green" if count == args.runs else ("yellow" if count > 1 else "dim")
        table.add_row(ticker, f"[{style}]{count}[/]", nucleo)
    console.print(table)

    pct = (avg_overlap / size * 100) if size else 0
    summary = (
        f"[bold]Dos corridas cualquiera comparten, en promedio, "
        f"{avg_overlap:.1f} de {size} acciones[/] ({pct:.0f}%).\n\n"
        f"[bold]{len(stable_core)} acciones[/] aparecieron en TODAS las corridas "
        f"(el núcleo estable): {', '.join(stable_core) if stable_core else '—'}\n\n"
        f"[dim]Referencia Clase 1 (prompt suelto): dos equipos cualquiera "
        f"compartían {BASELINE_PROMPT_SUELTO}/10; con el mismo modelo, "
        f"{BASELINE_MISMO_MODELO}/10.[/]\n"
        f"Con proceso y criterios claros, la convergencia es mucho mayor. "
        f"Si quieres acercarte aún más a la repetición exacta, baja la [bold]temperatura[/] "
        f"de los agentes (en agents/*.md) hacia 0."
    )
    console.print(Panel(summary, title="📊 Resultado", border_style="bold green"))

    _save_summary(runs, freq, stable_core, avg_overlap, size, args.runs)


def _save_summary(runs, freq, stable_core, avg_overlap, size, n_runs):
    """Guarda un resumen del experimento en output/."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"consistencia_{stamp}.md"

    lines = [
        f"# Experimento de consistencia — {stamp}",
        "",
        f"- **Corridas:** {n_runs}",
        f"- **Solape promedio entre dos carteras:** {avg_overlap:.1f} de {size} "
        f"({avg_overlap / size * 100:.0f}%)" if size else "",
        f"- **Núcleo estable (en todas las corridas):** "
        f"{', '.join(stable_core) if stable_core else '—'}",
        "",
        "## Cartera de cada corrida",
        "",
    ]
    for i, tickers in enumerate(runs, start=1):
        lines.append(f"- **Corrida {i}:** {', '.join(tickers)}")
    lines += ["", "## Frecuencia por acción", "", f"| Ticker | Apariciones (de {n_runs}) |", "|---|---|"]
    for ticker, count in freq.most_common():
        lines.append(f"| {ticker} | {count} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"\n[bold green]✓ Resumen guardado en:[/] {path}")


if __name__ == "__main__":
    main()
