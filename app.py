import os

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from src.routes.compras import compras_bp
from src.routes.serpapi import serpapi_bp


def create_app() -> Flask:
    project_dir = Path(__file__).resolve().parent
    dotenv_path = project_dir / ".env"
    if not dotenv_path.exists():
        dotenv_path = project_dir / ".env.example"
    load_dotenv(dotenv_path=dotenv_path)

    app = Flask(__name__)
    app.register_blueprint(compras_bp)
    app.register_blueprint(serpapi_bp)
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=True, port=port)

