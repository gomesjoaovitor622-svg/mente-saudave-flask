"""Compatibilidade: mantem o antigo ``python run.py`` funcionando.

O ponto de entrada oficial do projeto e o arquivo ``app.py`` (na raiz).
Este modulo apenas reexporta a aplicacao (para servidores WSGI que apontam
para ``run:app``) e, quando executado diretamente, delega para ``app.py``.
"""

from app import create_app

app = create_app()
application = app

if __name__ == "__main__":
    import runpy
    from pathlib import Path

    # Executa o app.py como se fosse o programa principal, reaproveitando
    # exatamente a mesma configuracao de host, porta e debug.
    runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
