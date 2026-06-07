# 🧠 Cómo funciona este sistema

Esta guía conecta lo que viste en la presentación de clase con el código real.

## Agente, Skills y Tools

> *El AGENTE es el trabajador. Las SKILLS son lo que sabe hacer. Las TOOLS son las
> herramientas que usa para hacerlo.*

En este repo eso se traduce así:

| Concepto de clase | En el código | Ejemplo |
|-------------------|--------------|---------|
| **Agente** | Un archivo en `agents/` + la clase `Agent` (`src/agent.py`) | `agents/quant.md` |
| **Skills** | El **prompt** del agente (el texto bajo el frontmatter) | "Eres el Analista Cuantitativo..." |
| **Tools** | Funciones Python en `src/tools.py` que el agente puede ejecutar | `compute_metrics()` |

Un agente, por sí solo, solo "piensa" (genera texto). Las **tools** le dan manos: le
permiten bajar precios reales y calcular métricas. El modelo no ejecuta código —
**pide** que ejecutemos una tool, nosotros la corremos y le devolvemos el resultado.
Eso se llama *function calling* y vive en el loop de `src/agent.py`.

## El equipo de 4 agentes

No hay un solo prompt gigante. Hay un **equipo**, igual que en una gestora real. Cada
agente recibe el trabajo del anterior como contexto y construye sobre él:

```
🎯 PORTFOLIO MANAGER  define la misión: "arma una cartera de 10 acciones"
        │
        ▼
1 · RESEARCH   →  parte del universo (config.yaml), baja datos y propone candidatas
        │
        ▼
2 · QUANT      →  mide retorno, volatilidad, Sharpe y correlación de las candidatas
        │
        ▼
3 · RISK       →  descarta lo demasiado volátil, correlacionado o concentrado
        │
        ▼
🎯 PORTFOLIO MANAGER  →  integra todo, asigna pesos y explica cada decisión
```

Quién coordina este flujo es el **orquestador** (`src/orchestrator.py`). Por eso, ante
el mismo objetivo, el resultado es mucho más robusto y explicable que un prompt suelto:
**el proceso está escrito y cada paso tiene un criterio claro.**

## Por qué esto es mejor que un prompt suelto

En la Clase 1 vimos que 18 equipos, con el mismo dato y el mismo encargo, produjeron 18
carteras distintas: lo que no especificas, la IA lo asume. Aquí **nada queda al azar
implícito**:

- El **rol** de cada agente está escrito.
- Los **criterios** (qué es buen perfil, qué riesgo es inaceptable) están escritos.
- El **orden** y los **límites** (peso máximo, tamaño de cartera) están en `config.yaml`.

Sigues sin obtener dos carteras idénticas (los LLMs tienen *temperatura*, recuerda la
Clase 1), pero ahora **entiendes y controlas** de dónde viene cada decisión.

## El recorrido de una corrida

1. `run.py` llama a `run_pipeline()` en `src/orchestrator.py`.
2. El orquestador crea cada `Agent` leyendo su archivo `.md`.
3. Cada agente conversa con el LLM (vía `src/llm.py` → litellm → tu proveedor) y, si lo
   necesita, ejecuta tools (`src/tools.py`).
4. Verás en pantalla qué tool usó cada agente y su conclusión.
5. El Portfolio Manager entrega la cartera final, que se guarda en `output/`.

¿Quieres cambiar el comportamiento? No toques `src/`. Edita los **agentes** y el
**config**. Eso se explica en [COMO_EDITAR_AGENTES.md](COMO_EDITAR_AGENTES.md).
