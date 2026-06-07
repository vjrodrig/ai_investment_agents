"""
EL ORQUESTADOR (Portfolio Manager / PM).

Coordina al equipo de agentes. No es una "línea de montaje" rígida: cada agente
recibe el trabajo de los anteriores como contexto y construye sobre él. El flujo es:

    Research  ->  Quant  ->  Risk  ->  Portfolio Manager

Cada turno se imprime en pantalla (con rich) para que veas al equipo trabajando, y
ADEMÁS se registra en un transcript que se guarda en output/proceso_<fecha>.md, para
que los alumnos puedan revisar después todo el proceso de generación (qué tools usó
cada agente, qué datos obtuvo y a qué conclusión llegó). La cartera final del PM se
guarda en output/cartera_<fecha>.md.
"""

from __future__ import annotations

import re
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

# Largo máximo (caracteres) de un resultado de tool en el transcript, para que sea legible.
TOOL_RESULT_MAX = 800


def _run_agent(
    name: str, task: str, transcript: list, verbose: bool, temperatures=None
) -> str:
    """
    Corre un agente, registra su turno en `transcript` y (si verbose) lo muestra.

    `temperatures` (opcional) sobreescribe la temperatura del agente sin tocar su
    archivo: puede ser un float (se aplica a todos) o un dict {nombre_agente: temp}.
    Lo usa el experimento de temperatura.

    Devuelve la respuesta final (texto) del agente.
    """
    agent = Agent(name)
    if isinstance(temperatures, dict) and name in temperatures:
        agent.temperature = temperatures[name]
    elif isinstance(temperatures, (int, float)):
        agent.temperature = temperatures

    color = AGENT_COLORS.get(name, "white")
    turn = {"name": name, "role": agent.role, "model": agent.model, "tools": []}

    if verbose:
        console.print(
            Rule(
                f"[bold {color}]{agent.role}[/]  ({agent.model}, temp={agent.temperature})",
                style=color,
            )
        )

    def on_tool(tool_name: str, arguments: dict, result: str):
        # Se registra todo en el transcript; en pantalla mostramos solo nombre + args.
        turn["tools"].append({"name": tool_name, "args": arguments, "result": result})
        if verbose:
            console.print(f"  [dim]🔧 usa tool[/] [bold]{tool_name}[/]  {arguments}")

    output = agent.run(task, on_tool=on_tool)
    turn["output"] = output
    transcript.append(turn)

    if verbose:
        console.print(Panel(output, border_style=color, title=f"{agent.role} concluye"))
    return output


def run_pipeline(verbose: bool = True, temperatures=None) -> dict:
    """
    Ejecuta el equipo completo.

    `temperatures` (opcional) sobreescribe las temperaturas de los agentes sin tocar
    sus archivos: un float para todos, o un dict {nombre_agente: temp}. Útil para el
    experimento que busca la mejor combinación de temperaturas.

    Devuelve un dict con:
        report          -> texto final del Portfolio Manager
        tickers         -> lista de tickers de la cartera final
        report_path     -> ruta del reporte guardado
        transcript_path -> ruta del log del proceso guardado
        transcript      -> lista estructurada de los turnos de cada agente
    """
    config = load_config()
    size = config["portfolio"]["size"]
    period = config["portfolio"]["lookback_period"]
    max_weight = config["portfolio"]["max_weight"]

    transcript: list = []

    if verbose:
        console.print(
            Panel(
                f"[bold]Objetivo:[/] armar una cartera de {size} acciones.\n"
                f"Ventana de análisis: {period}  ·  Peso máximo por acción: {max_weight:.0%}",
                title="🎯 Portfolio Manager asigna la misión al equipo",
                border_style="bold white",
            )
        )

    # 1 · RESEARCH ----------------------------------------------------------
    research = _run_agent(
        "research",
        f"Revisa el universo de inversión disponible y selecciona una lista corta "
        f"de candidatas con buen perfil (apunta a unas {size * 2} acciones). "
        f"Usa una ventana de {period}. Justifica brevemente cada elección.",
        transcript,
        verbose,
        temperatures,
    )

    # 2 · QUANT -------------------------------------------------------------
    quant = _run_agent(
        "quant",
        f"Estas son las candidatas del analista de Research:\n\n{research}\n\n"
        f"Calcula las métricas cuantitativas (retorno, volatilidad, Sharpe, "
        f"correlación) de esas candidatas con una ventana de {period} y resume "
        f"cuáles tienen el mejor perfil riesgo/retorno.",
        transcript,
        verbose,
        temperatures,
    )

    # 3 · RISK --------------------------------------------------------------
    risk = _run_agent(
        "risk",
        f"Trabajo de Research:\n\n{research}\n\nAnálisis cuantitativo:\n\n{quant}\n\n"
        f"Evalúa el riesgo de la lista: descarta posiciones demasiado volátiles o "
        f"muy correlacionadas entre sí, y vigila la concentración (ninguna acción "
        f"debería superar un peso de {max_weight:.0%}). Entrega una lista depurada.",
        transcript,
        verbose,
        temperatures,
    )

    # 4 · PORTFOLIO MANAGER (síntesis final) --------------------------------
    pm = _run_agent(
        "portfolio_manager",
        f"Integra el trabajo del equipo y arma la cartera FINAL de exactamente "
        f"{size} acciones.\n\n"
        f"--- RESEARCH ---\n{research}\n\n"
        f"--- QUANT ---\n{quant}\n\n"
        f"--- RISK ---\n{risk}\n\n"
        f"Asigna un peso a cada acción (deben sumar 100%, ninguna sobre "
        f"{max_weight:.0%}) y explica en una frase por qué entra cada una. "
        f"Entrega el resultado como una tabla en markdown seguida de un resumen.",
        transcript,
        verbose,
        temperatures,
    )

    tickers = extract_final_tickers(pm, config)

    # Un mismo timestamp para emparejar el reporte y el log del proceso.
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = _save_report(pm, stamp, verbose)
    transcript_path = _save_transcript(transcript, stamp, config, verbose)

    return {
        "report": pm,
        "tickers": tickers,
        "report_path": report_path,
        "transcript_path": transcript_path,
        "transcript": transcript,
    }


def extract_final_tickers(report: str, config: dict) -> list[str]:
    """
    Extrae los tickers de la cartera final desde el reporte del PM.

    Estrategia principal: leer la línea 'TICKERS_FINALES: AAA, BBB, ...' que el PM
    debe incluir (ver agents/portfolio_manager.md). Si no está, cae a un respaldo:
    buscar tickers del universo dentro de las filas de la tabla markdown.
    """
    match = re.search(r"TICKERS_FINALES\s*:\s*(.+)", report, re.IGNORECASE)
    if match:
        raw = re.split(r"[,\s]+", match.group(1).strip())
        # Limpia adornos de markdown (backticks, asteriscos, etc.): deja solo letras.
        cleaned = [re.sub(r"[^A-Za-z]", "", t).upper() for t in raw]
        return [t for t in cleaned if t]

    # Respaldo: matchear tickers del universo solo en las filas de tabla (líneas con '|').
    universe = {t.upper() for t in config["universe"]["tickers"]}
    found: list[str] = []
    for line in report.splitlines():
        if "|" not in line:
            continue
        for token in re.findall(r"[A-Z]{1,5}", line):
            if token in universe and token not in found:
                found.append(token)
    return found


def _save_report(report: str, stamp: str, verbose: bool) -> str:
    """Guarda el reporte final del PM en output/."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"cartera_{stamp}.md"
    path.write_text(f"# Cartera generada — {stamp}\n\n{report}\n", encoding="utf-8")
    if verbose:
        console.print(f"\n[bold green]✓ Cartera guardada en:[/] {path}")
    return str(path)


def _save_transcript(transcript: list, stamp: str, config: dict, verbose: bool) -> str:
    """Guarda el log completo del proceso (la 'discusión' del equipo) en output/."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"proceso_{stamp}.md"

    size = config["portfolio"]["size"]
    period = config["portfolio"]["lookback_period"]
    max_weight = config["portfolio"]["max_weight"]
    model = config["llm"]["model"]

    lines = [
        f"# Proceso de generación — {stamp}",
        "",
        "Log completo de la discusión del equipo de agentes. Cada sección es el turno "
        "de un agente: qué tools usó, qué datos obtuvo y a qué conclusión llegó.",
        "",
        f"- **Objetivo:** cartera de {size} acciones",
        f"- **Ventana:** {period}  ·  **Peso máximo:** {max_weight:.0%}",
        f"- **Modelo:** `{model}`",
        "",
    ]

    for i, turn in enumerate(transcript, start=1):
        lines.append("---")
        lines.append(f"## {i} · {turn['role']}  (`{turn['model']}`)")
        lines.append("")
        if turn["tools"]:
            lines.append("**Tools usadas:**")
            lines.append("")
            for call in turn["tools"]:
                result = call["result"]
                if len(result) > TOOL_RESULT_MAX:
                    result = result[:TOOL_RESULT_MAX] + " …(truncado)"
                lines.append(f"- `{call['name']}({call['args']})`")
                lines.append("  ```json")
                lines.append(f"  {result}")
                lines.append("  ```")
            lines.append("")
        else:
            lines.append("_Este agente no usó tools (su trabajo es sintetizar)._")
            lines.append("")
        lines.append("**Conclusión:**")
        lines.append("")
        lines.append(turn["output"])
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    if verbose:
        console.print(f"[bold green]✓ Log del proceso guardado en:[/] {path}")
    return str(path)
