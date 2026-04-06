from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_env(project_dir: Path | None = None) -> None:
    """Carrega variáveis de ambiente a partir de `.env` ou `.env.example`."""
    if project_dir is None:
        project_dir = Path(__file__).resolve().parents[2]
    dotenv_path = project_dir / ".env"
    if not dotenv_path.exists():
        dotenv_path = project_dir / ".env.example"
    load_dotenv(dotenv_path=dotenv_path)


def get_serpapi_api_key() -> str:
    return os.getenv("SERPAPI_API_KEY", "").strip()


def get_port(default: int = 5001) -> int:
    """Porta HTTP do Flask. O default 5001 evita conflito com AirPlay no macOS (5000 → 403)."""
    return int(os.getenv("PORT", str(default)))

