"""
============================================================================
Gerador do pacote ZIP de entrega - Mente Saudavel
============================================================================
Monta o arquivo de entrega seguindo a regra de nomenclatura da atividade:

    [nome inicial de cada membro separado por _].[nome do sistema].zip

Exemplos
--------
    python scripts/gerar_zip.py --membros "Joao Maria Pedro Ana"
    -> Joao_Maria_Pedro_Ana.Mente_Saudavel.zip

    python scripts/gerar_zip.py --membros "Joao Maria" --saida "C:/Entregas"
    -> C:/Entregas/Joao_Maria.Mente_Saudavel.zip

O script inclui apenas os arquivos do projeto e ignora automaticamente
ambiente virtual, repositorio Git, caches, segredos (.env) e arquivos
temporarios. Assim o ZIP fica limpo e pode ser enviado ao professor.
============================================================================
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SYSTEM_NAME = "Mente_Saudavel"

# Pastas e arquivos que nunca devem entrar na entrega.
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".idea",
    ".vscode",
}

# Padroes de arquivo ignorados (segredos, caches, temporarios).
EXCLUDED_PATTERNS = (
    ".env",
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.tmp",
    "*.bak",
    "Thumbs.db",
    ".DS_Store",
)


def _slug(name: str) -> str:
    """Converte um nome em algo seguro para nome de arquivo.

    Remove acentos, espacos nas pontas e caracteres invalidos no Windows,
    preservando letras e numeros. Ex.: "João Vitor" -> "Joao_Vitor".
    """
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", ascii_name).strip("_")
    return cleaned or "Membro"


def build_zip_name(members: list[str]) -> str:
    """Monta o nome do ZIP conforme a regra da atividade."""
    if not members:
        raise ValueError("Informe ao menos um membro com --membros.")
    initials = [_slug(member) for member in members]
    return "_".join(initials) + f".{SYSTEM_NAME}.zip"


def _should_skip(path: Path) -> bool:
    """Decide se um arquivo/pasta deve ficar fora do ZIP."""
    relative = path.relative_to(BASE_DIR)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True
    for pattern in EXCLUDED_PATTERNS:
        if path.match(pattern):
            return True
    return False


def create_zip(destination: Path) -> Path:
    """Cria o ZIP com todos os arquivos validos do projeto."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(BASE_DIR.rglob("*")):
            if not path.is_file() or _should_skip(path):
                continue
            # O proprio ZIP gerado nao deve ser incluido.
            if path.resolve() == destination.resolve():
                continue
            archive.write(path, path.relative_to(BASE_DIR).as_posix())
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera o ZIP de entrega do projeto Mente Saudavel."
    )
    parser.add_argument(
        "--membros",
        required=True,
        help='Nomes dos integrantes separados por espaco. Ex.: "Joao Maria Pedro Ana"',
    )
    parser.add_argument(
        "--saida",
        default=str(BASE_DIR),
        help="Pasta onde o ZIP sera gravado (padrao: raiz do projeto).",
    )
    args = parser.parse_args()

    members = args.membros.split()
    try:
        filename = build_zip_name(members)
    except ValueError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2

    destination = Path(args.saida) / filename
    result = create_zip(destination)
    size_mb = result.stat().st_size / (1024 * 1024)
    print(f"ZIP gerado: {result}")
    print(f"Tamanho: {size_mb:.2f} MB")
    print("Conteudo: app/, database/, docs/, postman/, scripts/, tests/ e arquivos raiz.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
