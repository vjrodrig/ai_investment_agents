"""
Carga de configuración y secretos.

- Lee  config.yaml  (modelo, universo, parámetros de cartera).
- Carga las API keys desde  .env  (vía python-dotenv) hacia variables de entorno.

Las keys NUNCA viven en el código ni en config.yaml: solo en tu archivo .env local,
que está ignorado por git. litellm las lee automáticamente del entorno.
"""

from pathlib import Path

import yaml
from dotenv import load_dotenv

# Raíz del proyecto (un nivel arriba de src/).
ROOT = Path(__file__).resolve().parent.parent

# Carga el archivo .env (si existe) hacia las variables de entorno del proceso.
load_dotenv(ROOT / ".env")


def load_config() -> dict:
    """Devuelve el contenido de config.yaml como diccionario."""
    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            "No se encontró config.yaml en la raíz del proyecto."
        )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# Carpetas usadas por el resto del sistema.
AGENTS_DIR = ROOT / "agents"
OUTPUT_DIR = ROOT / "output"
