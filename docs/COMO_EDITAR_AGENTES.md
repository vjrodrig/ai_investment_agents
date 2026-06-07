# ✏️ Cómo editar (y crear) agentes

Esta es la parte divertida: experimentar. Todo lo que cambia el comportamiento del
equipo está en dos lugares — la carpeta `agents/` y el archivo `config.yaml` — **no**
en `src/`.

> Después de cada cambio, vuelve a correr `python run.py` y compara el resultado.

---

## 1. Anatomía de un agente

Cada agente es un archivo `.md` con dos partes:

```markdown
---                                   ←┐
name: research                         │
role: Analista de Research             │  FRONTMATTER (configuración)
model: default                         │
temperature: 0.4                       │
tools: [list_universe, get_market_data]│
---                                   ←┘
Eres el Analista de Research...        ←  PROMPT (las "skills": lo que el agente sabe hacer)
```

| Campo | Qué hace |
|-------|----------|
| `name` | Identificador interno (debe coincidir con el nombre del archivo). |
| `role` | Nombre legible que se muestra en pantalla. |
| `model` | `default` hereda `config.yaml`. O pon otro, ej. `openai/gpt-4o`. |
| `temperature` | 0 = predecible y consistente; 1 = creativo. (Recap Clase 1.) |
| `tools` | Lista de tools que este agente puede usar (ver más abajo). |

---

## 2. Cosas que puedes probar

**Cambiar la personalidad / criterios de un agente** — edita el prompt.
Ej.: en `agents/risk.md`, hazlo más estricto: *"Descarta cualquier acción con
volatilidad anualizada sobre 30%."* Vuelve a correr y mira cómo cambia la lista.

**Cambiar la temperatura** — sube la del Research a `0.8` y observa si propone
candidatas más variadas; baja la del Quant a `0.0` para máxima consistencia.

**Mezclar modelos** — pon `model: openai/gpt-4o` en un agente y deja el resto en
Claude. Necesitas la key de cada proveedor que uses en tu `.env`.

**Cambiar el universo o los límites** — en `config.yaml`: agrega/quita tickers,
cambia `portfolio.size` a 5, o baja `portfolio.max_weight` a `0.10`.

---

## 3. Las tools disponibles

Los valores válidos para el campo `tools:` de un agente son:

| Tool | Qué hace |
|------|----------|
| `list_universe` | Devuelve la lista de tickers candidatos de `config.yaml`. |
| `get_market_data` | Baja precio y retorno reciente de unos tickers (Yahoo Finance). |
| `compute_metrics` | Calcula retorno, volatilidad, Sharpe y correlación. |

Si un agente no declara una tool, no puede usarla. El Portfolio Manager, por ejemplo,
no tiene tools (`tools: []`): su trabajo es **sintetizar**, no bajar datos.

---

## 4. Crear un agente nuevo (avanzado)

Supón que quieres agregar un agente **ESG** que evalúe sostenibilidad.

1. **Crea el archivo** `agents/esg.md` (copia uno existente y edita el prompt y el
   frontmatter; pon `name: esg`).
2. **Conéctalo al flujo** en `src/orchestrator.py`: dentro de `run_pipeline()`, agrega
   un paso como los demás, pasándole el contexto que necesite:
   ```python
   esg = _run_agent_with_display(
       "esg",
       f"Evalúa la sostenibilidad de estas candidatas:\n\n{research}",
   )
   ```
   y luego incluye `esg` en el contexto que recibe el Portfolio Manager.
3. (Opcional) Si tu agente necesita una **tool nueva**, agrégala en `src/tools.py`:
   escribe la función, su schema en `TOOL_SCHEMAS` y regístrala en `TOOL_REGISTRY`.

---

## 5. Regla de oro

> Para cambiar **qué hace** el equipo → edita `agents/` y `config.yaml`.
> Para cambiar **cómo funciona** la maquinaria → toca `src/` (rara vez necesario).

Si algo se rompe, el mensaje de error de `run.py` te dirá qué revisar.
