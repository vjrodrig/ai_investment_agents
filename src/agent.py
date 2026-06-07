"""
La clase Agent: un "trabajador" del equipo.

Un agente se define enteramente en un archivo de la carpeta agents/ (ej.
agents/research.md). Ese archivo tiene dos partes:

    ---
    name: research
    role: Analista de Research
    model: default        # "default" hereda config.yaml
    temperature: 0.3
    tools: [list_universe, get_market_data]
    ---
    Eres el analista de Research...   <- el prompt (las "skills" del agente)

Esta clase:
  1. Lee y parsea ese archivo.
  2. Arma la conversación (system prompt + la tarea que le da el orquestador).
  3. Corre el "loop de tools": habla con el modelo, ejecuta las tools que pida y
     repite hasta que el agente entregue su respuesta final en texto.
"""

from __future__ import annotations

import json

import yaml

from .config import AGENTS_DIR, load_config
from .llm import chat
from .tools import run_tool, schemas_for

# Tope de iteraciones del loop de tools, por si el modelo se queda en bucle.
MAX_TOOL_ITERATIONS = 8


def _parse_agent_file(path) -> tuple[dict, str]:
    """Separa el frontmatter YAML (entre ---) del cuerpo (el prompt)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path.name} debe empezar con frontmatter '---'.")
    _, frontmatter, body = text.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    return meta, body.strip()


class Agent:
    """Un agente cargado desde un archivo de agents/."""

    def __init__(self, name: str):
        config = load_config()
        meta, prompt = _parse_agent_file(AGENTS_DIR / f"{name}.md")

        self.name = name
        self.role = meta.get("role", name)
        self.prompt = prompt
        self.tool_names = meta.get("tools", []) or []

        # "default" hereda el modelo/temperatura globales de config.yaml.
        model = meta.get("model", "default")
        self.model = config["llm"]["model"] if model == "default" else model
        self.temperature = meta.get("temperature", config["llm"]["temperature"])
        self.max_tokens = config["llm"]["max_tokens"]

    def run(self, task: str, on_tool=None) -> str:
        """
        Ejecuta al agente sobre una tarea y devuelve su respuesta final (texto).

        `on_tool(name, arguments)` es un callback opcional para que el orquestador
        muestre en pantalla qué tool usó el agente (transparencia pedagógica).
        """
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": task},
        ]
        tools = schemas_for(self.tool_names)

        for _ in range(MAX_TOOL_ITERATIONS):
            message = chat(
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            messages.append(message.model_dump())

            tool_calls = message.tool_calls or []
            if not tool_calls:
                # Sin más tools que ejecutar: esta es la respuesta final.
                return message.content or ""

            # Ejecuta cada tool pedida y devuelve su resultado al modelo.
            for call in tool_calls:
                args = json.loads(call.function.arguments or "{}")
                if on_tool:
                    on_tool(call.function.name, args)
                result = run_tool(call.function.name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )

        return "[El agente alcanzó el máximo de iteraciones de tools.]"
