"""
Punto de entrada del sistema de agentes de inversión.

Uso:
    python run.py

Requisitos previos:
    1. pip install -r requirements.txt
    2. cp .env.example .env  y pega tu API key
    3. (opcional) ajusta config.yaml y los agentes en agents/

El programa corre el equipo Research -> Quant -> Risk -> Portfolio Manager y
guarda la cartera final en output/.
"""

import sys

from rich.console import Console

from src.orchestrator import run_pipeline

console = Console()


def main():
    console.print("[bold]🏦 Sistema de Agentes de Inversión[/]\n")
    try:
        run_pipeline()
    except Exception as exc:  # noqa: BLE001 - mensaje amable para el alumno
        console.print(f"\n[bold red]Error:[/] {exc}")
        console.print(
            "\n[yellow]Revisa que:[/]\n"
            "  • Instalaste las dependencias: pip install -r requirements.txt\n"
            "  • Copiaste .env.example a .env y pegaste tu API key\n"
            "  • El modelo en config.yaml corresponde a la key que pusiste\n"
            "  • Tienes conexión a internet (los datos vienen de Yahoo Finance)"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
