"""
============================================================================
Banco local do projeto - Mente Saudavel
============================================================================
Este script cria e gerencia um cluster PostgreSQL exclusivo do projeto, sem
depender da senha do PostgreSQL que ja existe na maquina. Ele e usado pelas
tarefas do VS Code (``.vscode/tasks.json``) e pode ser executado manualmente:

    python scripts/banco_local.py configurar   # cria o cluster, o banco e carrega os scripts
    python scripts/banco_local.py iniciar      # sobe o PostgreSQL local
    python scripts/banco_local.py parar        # desliga o PostgreSQL local
    python scripts/banco_local.py status       # mostra se esta no ar
    python scripts/banco_local.py recriar      # apaga o banco e recarrega os scripts

POR QUE UM CLUSTER PROPRIO?
---------------------------
O PostgreSQL instalado no Windows costuma pedir uma senha definida na
instalacao, que pode nao ser conhecida. Um cluster separado, na pasta de dados
do usuario, usa a senha "postgres" apenas para o projeto e nao interfere em
nenhum outro banco da maquina.

O cluster fica em ``%LOCALAPPDATA%\\MenteSaudavel\\pgdata`` (Windows) ou em
``~/.local/share/mente-saudavel/pgdata`` (Linux/macOS), fora do OneDrive, para
evitar sincronizacao de arquivos de banco em tempo real.
============================================================================
"""

from __future__ import annotations

import argparse
import getpass
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# O console do Windows costuma usar cp1252. As ferramentas do PostgreSQL
# escrevem em UTF-8, entao a saida precisa ser reconfigurada para nao quebrar
# com acentos ou caracteres de substituicao.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - console antigo
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
ENV_FILE = BASE_DIR / ".env"

DB_NAME = "mente_saudavel"
TEST_DB_NAME = "mente_saudavel_test"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DEFAULT_PORT = 55433


def _data_dir() -> Path:
    """Pasta de dados do cluster local (fora do repositorio/OneDrive)."""
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "MenteSaudavel" / "pgdata"
    base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "mente-saudavel" / "pgdata"


def _find_bin(name: str) -> str:
    """Localiza um executavel do PostgreSQL no PATH ou na instalacao padrao."""
    found = shutil.which(name)
    if found:
        return found

    candidates: list[Path] = []
    if os.name == "nt":
        for root in (Path(r"C:\Program Files\PostgreSQL"), Path(r"C:\Program Files (x86)\PostgreSQL")):
            if root.exists():
                candidates.extend(sorted(root.glob(f"*/bin/{name}.exe"), reverse=True))
    else:
        candidates.extend(
            [
                Path(f"/usr/lib/postgresql/*/bin/{name}"),
                Path(f"/usr/local/pgsql/bin/{name}"),
                Path(f"/opt/homebrew/opt/postgresql*/bin/{name}"),
            ]
        )
        expanded: list[Path] = []
        for pattern in candidates:
            expanded.extend(Path("/").glob(str(pattern).lstrip("/")))
        candidates = expanded

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        f"Nao encontrei '{name}'. Instale o PostgreSQL 14+ e adicione a pasta bin ao PATH."
    )


def _run(
    command: list[str],
    *,
    env: dict | None = None,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """Executa um comando mostrando a saida (UTF-8) no terminal.

    ``capture=False`` e obrigatorio para ``pg_ctl start``: o servidor iniciado
    herda os descritores do processo pai e, com ``capture_output=True``, o
    ``communicate()`` esperaria o pipe fechar - ou seja, ficaria travado ate o
    PostgreSQL ser desligado.
    """
    merged = os.environ.copy()
    if env:
        merged.update(env)
    if capture:
        result = subprocess.run(
            command,
            env=merged,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
    else:
        result = subprocess.run(command, env=merged)
    if check and result.returncode != 0:
        raise RuntimeError(f"Falhou: {' '.join(command)}")
    return result


def _pg_env(port: int) -> dict:
    return {
        "PGPASSWORD": DB_PASSWORD,
        "PGCLIENTENCODING": "UTF8",
        "PGPORT": str(port),
        # Evita que os "DROP ... does not exist, skipping" poluam o terminal.
        "PGOPTIONS": "-c client_min_messages=warning",
    }


def _is_running(data_dir: Path) -> bool:
    pg_ctl = _find_bin("pg_ctl")
    result = subprocess.run(
        [pg_ctl, "status", "-D", str(data_dir)],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return result.returncode == 0


def _wait_ready(port: int, timeout: float = 30.0) -> None:
    psql = _find_bin("psql")
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            [psql, "-h", "127.0.0.1", "-p", str(port), "-U", DB_USER, "-d", "postgres", "-tAc", "SELECT 1"],
            env={**os.environ, **_pg_env(port)},
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError("O PostgreSQL local nao ficou pronto a tempo. Veja o server.log.")


def _init_cluster(data_dir: Path, port: int) -> None:
    if (data_dir / "PG_VERSION").exists():
        print(f"Cluster ja existe em: {data_dir}")
        return
    data_dir.parent.mkdir(parents=True, exist_ok=True)
    initdb = _find_bin("initdb")
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
        handle.write(DB_PASSWORD + "\n")
        pwfile = handle.name
    try:
        print(f"Criando cluster PostgreSQL em: {data_dir}")
        _run(
            [
                initdb,
                "-D",
                str(data_dir),
                "-U",
                DB_USER,
                "--auth=scram-sha-256",
                f"--pwfile={pwfile}",
                "--encoding=UTF8",
                "--locale=C",
            ]
        )
    finally:
        Path(pwfile).unlink(missing_ok=True)


def _start(data_dir: Path, port: int) -> None:
    if _is_running(data_dir):
        print(f"PostgreSQL local ja esta no ar (porta {port}).")
        return
    pg_ctl = _find_bin("pg_ctl")
    log = data_dir / "server.log"
    print(f"Iniciando PostgreSQL local na porta {port}...")
    _run(
        [
            pg_ctl,
            "-D",
            str(data_dir),
            "-o",
            f"-p {port} -c listen_addresses=127.0.0.1",
            "-l",
            str(log),
            "start",
        ],
        capture=False,
    )
    _wait_ready(port)
    print(f"PostgreSQL local pronto: 127.0.0.1:{port}")


def _stop(data_dir: Path) -> None:
    if not (data_dir / "PG_VERSION").exists():
        print("Cluster local ainda nao foi criado.")
        return
    if not _is_running(data_dir):
        print("PostgreSQL local ja esta parado.")
        return
    pg_ctl = _find_bin("pg_ctl")
    print("Parando PostgreSQL local...")
    _run([pg_ctl, "-D", str(data_dir), "-m", "fast", "stop"])


def _psql(port: int, database: str, args: list[str]) -> subprocess.CompletedProcess:
    psql = _find_bin("psql")
    return _run(
        [psql, "-h", "127.0.0.1", "-p", str(port), "-U", DB_USER, "-d", database, *args],
        env=_pg_env(port),
    )


def _database_exists(port: int, db_name: str = DB_NAME) -> bool:
    result = subprocess.run(
        [
            _find_bin("psql"),
            "-h",
            "127.0.0.1",
            "-p",
            str(port),
            "-U",
            DB_USER,
            "-d",
            "postgres",
            "-tAc",
            f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'",
        ],
        env={**os.environ, **_pg_env(port)},
        text=True,
        capture_output=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "1"


def _create_database(port: int, db_name: str = DB_NAME) -> None:
    if _database_exists(port, db_name):
        print(f"Banco '{db_name}' ja existe.")
        return
    print(f"Criando banco '{db_name}'...")
    _psql(
        port,
        "postgres",
        [
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            f"CREATE DATABASE {db_name} WITH ENCODING 'UTF8' TEMPLATE template0",
        ],
    )


def _load_scripts(port: int, *, db_name: str = DB_NAME, recriar: bool = False) -> None:
    if recriar and _database_exists(port, db_name):
        print(f"Recriando banco '{db_name}'...")
        _psql(
            port,
            "postgres",
            ["-v", "ON_ERROR_STOP=1", "-c", f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE)"],
        )
        _create_database(port, db_name)
    else:
        _create_database(port, db_name)

    scripts = [
        DATABASE_DIR / "01_schema.sql",
        DATABASE_DIR / "02_views.sql",
        DATABASE_DIR / "03_procedures.sql",
        DATABASE_DIR / "04_seed.sql",
    ]
    for script in scripts:
        print(f"Executando {script.name} em '{db_name}'...")
        _psql(port, db_name, ["-v", "ON_ERROR_STOP=1", "-q", "-f", str(script)])


def _write_env(port: int, *, force: bool = False) -> None:
    if ENV_FILE.exists() and not force:
        print(f".env ja existe ({ENV_FILE}); mantido. Use --force para sobrescrever.")
        return
    content = f"""# Gerado por scripts/banco_local.py
# Banco PostgreSQL exclusivo do projeto (nao usa a senha do PostgreSQL do sistema).
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=chave-local-do-projeto-mente-saudavel
PORT=5000

DB_HOST=127.0.0.1
DB_PORT={port}
DB_NAME={DB_NAME}
DB_USER={DB_USER}
DB_PASSWORD={DB_PASSWORD}
"""
    ENV_FILE.write_text(content, encoding="utf-8")
    print(f".env criado em: {ENV_FILE}")


def _port_from_args(args: argparse.Namespace) -> int:
    return args.port or DEFAULT_PORT


def comando_configurar(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir) if args.data_dir else _data_dir()
    port = _port_from_args(args)
    _init_cluster(data_dir, port)
    _start(data_dir, port)
    _load_scripts(port, recriar=args.recriar)
    if getattr(args, "com_teste", False):
        # O banco de teste e sempre recriado: assim a suite pytest parte de um
        # estado conhecido e nao depende de execucoes anteriores.
        _load_scripts(port, db_name=TEST_DB_NAME, recriar=True)
    _write_env(port, force=args.force)
    print("\nTudo pronto. No VS Code, execute a tarefa 'API: executar' ou pressione F5.")
    print(f"Painel: http://localhost:5000  |  API: http://localhost:5000/api")
    return 0


def comando_iniciar(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir) if args.data_dir else _data_dir()
    _start(data_dir, _port_from_args(args))
    return 0


def comando_parar(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir) if args.data_dir else _data_dir()
    _stop(data_dir)
    return 0


def comando_status(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir) if args.data_dir else _data_dir()
    if not (data_dir / "PG_VERSION").exists():
        print("Cluster local ainda nao foi criado. Rode: python scripts/banco_local.py configurar")
        return 1
    print(f"Pasta de dados: {data_dir}")
    print("No ar." if _is_running(data_dir) else "Parado.")
    return 0 if _is_running(data_dir) else 1


def comando_recriar(args: argparse.Namespace) -> int:
    args.recriar = True
    args.com_teste = True
    return comando_configurar(args)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gerencia o PostgreSQL local do projeto.")
    parser.add_argument("--data-dir", help="Pasta de dados do cluster (padrao: pasta do usuario).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Porta local (padrao: {DEFAULT_PORT}).")
    parser.add_argument("--force", action="store_true", help="Sobrescreve o .env existente.")
    sub = parser.add_subparsers(dest="comando", required=True)

    configurar = sub.add_parser("configurar", help="Cria o cluster, o banco e carrega os scripts.")
    configurar.add_argument("--recriar", action="store_true", help="Apaga e recria o banco.")
    configurar.add_argument(
        "--com-teste",
        action="store_true",
        help="Tambem cria/recria o banco de teste usado pelo pytest.",
    )
    configurar.set_defaults(func=comando_configurar)

    sub.add_parser("iniciar", help="Sobe o PostgreSQL local.").set_defaults(func=comando_iniciar)
    sub.add_parser("parar", help="Desliga o PostgreSQL local.").set_defaults(func=comando_parar)
    sub.add_parser("status", help="Mostra o estado do cluster.").set_defaults(func=comando_status)
    sub.add_parser("recriar", help="Recria o banco e recarrega os scripts.").set_defaults(func=comando_recriar)

    args = parser.parse_args()
    try:
        return args.func(args)
    except (FileNotFoundError, RuntimeError) as error:
        print(f"\nERRO: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
