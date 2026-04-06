from pathlib import Path

from flask import Flask

from src.config.env import get_port, load_env
from src.routes.price import compras_bp, serpapi_bp


def create_app() -> Flask:
    project_dir = Path(__file__).resolve().parent
    load_env(project_dir)

    app = Flask(__name__)
    app.register_blueprint(compras_bp)
    app.register_blueprint(serpapi_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=get_port())
