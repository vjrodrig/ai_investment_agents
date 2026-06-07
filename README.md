# 🏦 Sistema de Agentes de Inversión

Un equipo de **agentes de IA** que construye una cartera de acciones, paso a paso.
Material de la **Clase 2 — "Técnicas avanzadas: agentes y skills"** del curso *IA
Generativa y Mercado de Capitales* (Magíster en Finanzas, Universidad de los Andes).

En la Clase 1 vimos que cuando le pides a una IA *"arma una cartera"* con un prompt
suelto, cada quien obtiene algo distinto: la IA rellena los huecos que dejaste. La
solución no es un prompt más largo, sino **ponerle proceso**: dividir la tarea en
roles con criterios claros. Eso es exactamente lo que hace este repo.

```
            🎯 PORTFOLIO MANAGER  (coordina y decide)
                        │
        ┌───────────────┼───────────────┐
   1·RESEARCH       2·QUANT          3·RISK
   filtra el       mide riesgo      descarta lo
   universo        y retorno        peligroso
```

Cada agente es un **trabajador** con un **rol**, unas **skills** (lo que sabe hacer,
escrito en su prompt) y unas **tools** (lo que puede ejecutar: bajar precios, calcular
métricas). Lee [docs/COMO_FUNCIONA.md](docs/COMO_FUNCIONA.md) para el detalle.

---

## 🚀 Cómo correrlo (5 pasos)

> Necesitas Python 3.9+ instalado.

```bash
# 1. Clona el repo y entra a la carpeta
git clone <URL-DEL-REPO>
cd ai_investment_agents

# 2. Crea un entorno virtual e instálalo
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Crea tu archivo de secretos a partir de la plantilla
cp .env.example .env

# 4. Abre .env y pega TU api key (de Claude, OpenAI o Gemini)

# 5. Corre el equipo
python run.py
```

Verás a cada agente trabajar en pantalla y, al final, en `output/` quedarán **dos
archivos**: la cartera (`cartera_<fecha>.md`) y el **log completo del proceso**
(`proceso_<fecha>.md`) con todo lo que discutió el equipo.

---

## 🔬 Ver el proceso y probar la consistencia

**1. El log del proceso.** Cada corrida guarda en `output/proceso_<fecha>.md` la
"discusión" completa del equipo: qué tools usó cada agente, qué datos obtuvo y a qué
conclusión llegó. Ábrelo para entender *cómo* se generó la cartera, no solo el
resultado.

**2. ¿La cartera es estable?** En la Clase 1 vimos que un prompt suelto daba una
cartera distinta cada vez. Con **proceso**, eso cambia. Pruébalo:

```bash
python experimentos/consistencia.py --runs 3
```

Corre el sistema varias veces y mide cuántas acciones comparten las carteras (la misma
métrica de la presentación: *"acciones en común, de 10"*). Verás un **núcleo estable**
de acciones que se repite. Si quieres acercarte aún más a la repetición exacta, baja la
`temperature` de los agentes hacia `0` (Recap Clase 1: temperatura = aleatoriedad).

---

## 🔑 ¿Qué API key necesito?

El sistema es **agnóstico del proveedor**: funciona con Claude, OpenAI o Gemini. Solo
necesitas **una** key, la del proveedor que elijas en [config.yaml](config.yaml):

| Proveedor | Línea en `config.yaml` (`llm.model`) | Dónde sacar la key |
|-----------|--------------------------------------|--------------------|
| Claude    | `anthropic/claude-sonnet-4-6`        | https://console.anthropic.com/ |
| OpenAI    | `openai/gpt-4o`                      | https://platform.openai.com/api-keys |
| Gemini    | `gemini/gemini-2.0-flash`            | https://aistudio.google.com/app/apikey |

Pega la key en tu archivo `.env` (en la línea correcta) y listo. Cambiar de proveedor
es cambiar **una línea** en `config.yaml`; el resto del código no cambia.

---

## ✏️ Lo importante: editar los agentes

El corazón de este repo es la carpeta [agents/](agents/). **Cada agente es un archivo
de texto que puedes leer y cambiar.** Por ejemplo, [agents/research.md](agents/research.md)
empieza así:

```markdown
---
name: research
role: Analista de Research
model: default          # hereda config.yaml, o pon otro: openai/gpt-4o
temperature: 0.4        # 0 = predecible, 1 = creativo
tools: [list_universe, get_market_data]
---
Eres el Analista de Research de un equipo de inversión...
```

Cambia el prompt, la temperatura o las tools, vuelve a correr `python run.py` y observa
cómo cambia el resultado. Guía completa en
[docs/COMO_EDITAR_AGENTES.md](docs/COMO_EDITAR_AGENTES.md).

---

## 🔒 Seguridad (este repo es público)

- **Nunca subas tu archivo `.env`.** Contiene tu API key. Ya está bloqueado por
  [.gitignore](.gitignore), pero revisa con `git status` antes de hacer commit: tu
  `.env` **no** debe aparecer.
- Las keys se leen **solo** del entorno (tu `.env` local). No hay ninguna key en el
  código ni en `config.yaml`, y nunca debe haberla.
- Si crees que filtraste una key, **revócala de inmediato** en el panel del proveedor
  y genera una nueva.

---

## 📁 Estructura del proyecto

```
ai_investment_agents/
├── README.md              ← estás aquí
├── config.yaml            ← modelo, universo de acciones y parámetros de cartera
├── .env.example           ← plantilla de keys (copia a .env)
├── run.py                 ← punto de entrada: python run.py
├── agents/                ← ⭐ los agentes (edita estos archivos)
│   ├── research.md
│   ├── quant.md
│   ├── risk.md
│   └── portfolio_manager.md
├── src/                   ← la "plomería" (normalmente no necesitas tocarla)
│   ├── config.py          ·  carga config.yaml y .env
│   ├── llm.py             ·  capa agnóstica (litellm) que habla con cualquier LLM
│   ├── agent.py           ·  lee un agente y corre su loop de tools
│   ├── tools.py           ·  las tools (Yahoo Finance, cálculo de métricas)
│   └── orchestrator.py    ·  coordina al equipo, imprime y registra cada turno
├── experimentos/
│   └── consistencia.py    ← corre el sistema N veces y mide si la cartera varía
├── docs/
│   ├── COMO_FUNCIONA.md
│   └── COMO_EDITAR_AGENTES.md
└── output/                ← carteras (cartera_*.md) y logs del proceso (proceso_*.md)
```

---

## ⚠️ Aviso

Este proyecto es **educativo**. No es asesoría financiera ni una recomendación de
inversión. Los datos provienen de Yahoo Finance y pueden tener errores o retrasos.
