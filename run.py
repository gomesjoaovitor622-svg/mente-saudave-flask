"""Ponto de entrada da aplicacao Mente Saudavel."""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=str(os.getenv("FLASK_DEBUG", "0")).lower() in {"1", "true", "yes"},
    )
