"""
EL ORQUESTADOR (Portfolio Manager / PM).

Coordina al equipo de agentes. No es una "línea de montaje" rígida: cada agente
recibe el trabajo de los anteriores como contexto y construye sobre él. El flujo es:

    Research  ->  Quant  ->  Risk  ->  Portfolio Manager

Cada turno se imprime en pantalla (con rich) para que veas al equipo trabajando:
qué tools usó cada agente y qué concluyó. Al final, el Portfolio Manager arma la
cartera y se guarda un reporte en output/.
"""

from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from .agent import Agent
from .config import OUTPUT_DIR, load_config

console = Console()

# Color por agente, solo para que la salida sea fácil de seguir.
AGENT_COLORS = {
    "research": "blue",
    "quant": "green",
    "risk": "red",
    "portfolio_manager": "magenta",
}


def _run_agent_with_display(name: str, task: str) -> str:
    """Corre un agente mostrando en vivo sus tools y su conclusión."""
    agent = Agent(name)
    color = AGENT_COLORS.get(name, "white")

    console.print(Rule(f"[bold {color}]{agent.role}[/]  ({agent.model})", style=color))

    def on_tool(tool_name: str, arguments: dict):
        console.print(f"  [dim]🔧 usa tool[/] [bold]{tool_name}[/]  {arguments}")

    output = agent.run(task, on_tool=on_tool)
    console.print(Panel(output, border_style=color, title=f"{agent.role} concluye"))
    return output


def run_pipeline() -> str:
    """Ejecuta el equipo completo y devuelve el reporte final del PM."""
    config = load_config()
    size = config["portfolio"]["size"]
    period = config["portfolio"]["lookback_period"]
    max_weight = config["portfolio"]["max_weight"]

    console.print(
        Panel(
            f"[bold]Objetivo:[/] armar una cartera de {size} acciones.\n"
            f"Ventana de análisis: {period}  ·  Peso máximo por acción: {max_weight:.0%}",
            title="🎯 Portfolio Manager asigna la misión al equipo",
            border_style="bold white",
        )
    )

    # 1 · RESEARCH ----------------------------------------------------------
    research = _run_agent_with_display(
        "research",
        f"Revisa el universo de inversión disponible y selecciona una lista corta "
        f"de candidatas con buen perfil (apunta a unas {size * 2} acciones). "
        f"Usa una ventana de {period}. Justifica brevemente cada elección.",
    )

    # 2 · QUANT -------------------------------------------------------------
    quant = _run_agent_with_display(
        "quant",
        f"Estas son las candidatas del analista de Research:\n\n{research}\n\n"
        f"Calcula las métricas cuantitativas (retorno, volatilidad, Sharpe, "
        f"correlación) de esas candidatas con una ventana de {period} y resume "
        f"cuáles tienen el mejor perfil riesgo/retorno.",
    )

    # 3 · RISK --------------------------------------------------------------
    risk = _run_agent_with_display(
        "risk",
        f"Trabajo de Research:\n\n{research}\n\nAnálisis cuantitativo:\n\n{quant}\n\n"
        f"Evalúa el riesgo de la lista: descarta posiciones demasiado volátiles o "
        f"muy correlacionadas entre sí, y vigila la concentración (ninguna acción "
        f"debería superar un peso de {max_weight:.0%}). Entrega una lista depurada.",
    )

    # 4 · PORTFOLIO MANAGER (síntesis final) --------------------------------
    pm = _run_agent_with_display(
        "portfolio_manager",
        f"Integra el trabajo del equipo y arma la cartera FINAL de exactamente "
        f"{size} acciones.\n\n"
        f"--- RESEARCH ---\n{research}\n\n"
        f"--- QUANT ---\n{quant}\n\n"
        f"--- RISK ---\n{risk}\n\n"
        f"Asigna un peso a cada acción (deben sumar 100%, ninguna sobre "
        f"{max_weight:.0%}) y explica en una frase por qué entra cada una. "
        f"Entrega el resultado como una tabla en markdown seguida de un resumen.",
    )

    _save_report(pm)
    return pm


def _save_report(report: str) -> str:
    """Guarda el reporte final del PM en output/ y avisa la ruta."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    path = OUTPUT_DIR / f"cartera_{stamp}.md"
    path.write_text(f"# Cartera generada — {stamp}\n\n{report}\n", encoding="utf-8")
    console.print(f"\n[bold green]✓ Reporte guardado en:[/] {path}")
    return str(path)
