"""
Capa LLM-agnóstica.

Toda la "plomería" de hablar con el modelo vive aquí, detrás de una sola función:
`chat()`. Usamos litellm, que traduce un mismo formato (estilo OpenAI) hacia
Claude, OpenAI o Gemini. Así, cambiar de proveedor es cambiar un string en
config.yaml — el resto del código no se entera.

Los alumnos normalmente NO necesitan tocar este archivo. Lo que editan son los
agentes (carpeta agents/) y config.yaml.
"""

from __future__ import annotations

import litellm

# litellm es verboso por defecto; lo silenciamos para que la salida sea limpia.
litellm.suppress_debug_info = True


def chat(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
):
    """
    Hace una llamada al modelo y devuelve el objeto `message` de la respuesta.

    Parámetros
    ----------
    model : str
        Modelo en formato proveedor/modelo (ej. "anthropic/claude-sonnet-4-6").
    messages : list[dict]
        Historial de conversación estilo OpenAI: [{"role": ..., "content": ...}, ...].
    tools : list[dict] | None
        Definiciones de tools (function-calling) que el modelo puede invocar.
    temperature : float
        Aleatoriedad de la respuesta (0 = predecible, 1 = creativo).
    max_tokens : int
        Largo máximo de la respuesta.

    Devuelve
    --------
    El `message` de la respuesta. Puede contener `.content` (texto) y/o
    `.tool_calls` (peticiones de ejecutar una tool).
    """
    response = litellm.completion(
        model=model,
        messages=messages,
        tools=tools or None,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message
