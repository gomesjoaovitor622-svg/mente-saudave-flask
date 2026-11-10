"""
============================================================================
Verificador do pacote de entrega - Mente Saudavel
============================================================================
Confere, sem dependencias externas, se o PDF e o ZIP estao prontos para
entrega:

    python scripts/verificar_entrega.py

Itens verificados:
  * PDF existe, tem tamanho razoavel e pelo menos 16 paginas;
  * ZIP segue o padrao de nome da atividade;
  * ZIP contem codigo, banco, documentacao, Postman, scripts e .vscode;
  * ZIP nao contem .env, .venv, caches, .git nem outro ZIP;
  * nomes da equipe aparecem no nome do pacote.

Saida: codigo 0 quando tudo esta certo; codigo 1 quando ha pendencias.
============================================================================
"""

from __future__ import annotations

import re
import sys
import unicodedata
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_PATH = BASE_DIR / "docs" / "Documentacao_Mente_Saudavel.pdf"
ZIP_DIR = BASE_DIR / "entrega"
MEMBROS = ["Jhennyfer", "Joao Vitor"]
SISTEMA = "Mente_Saudavel"

OBRIGATORIOS = [
    "app.py",
    "requirements.txt",
    "requirements-dev.txt",
    "README.md",
    "api.http",
    ".vscode/tasks.json",
    ".vscode/launch.json",
    "database/01_schema.sql",
    "database/02_views.sql",
    "database/03_procedures.sql",
    "database/04_seed.sql",
    "docs/Documentacao_Mente_Saudavel.pdf",
    "postman/mente-saudavel.postman_collection.json",
    "scripts/banco_local.py",
    "scripts/gerar_zip.py",
    "tests/test_api.py",
]

DIRETORIOS_PROIBIDOS = (".venv/", "__pycache__/", ".git/", ".pytest_cache/")


def _proibido(nome: str) -> bool:
    """Segredos, caches e pacotes antigos nao podem entrar na entrega."""
    return nome == ".env" or nome.endswith(".zip") or nome.startswith(DIRETORIOS_PROIBIDOS)


def _slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", ascii_name).strip("_")
    return cleaned or "Membro"


def nome_esperado() -> str:
    iniciais = [_slug(membro.split()[0]) for membro in MEMBROS]
    return "_".join(iniciais) + f".{SISTEMA}.zip"


def verificar_pdf() -> list[str]:
    problemas: list[str] = []
    if not PDF_PATH.exists():
        return [f"PDF nao encontrado: {PDF_PATH}"]
    data = PDF_PATH.read_bytes()
    tamanho_kb = len(data) / 1024
    if tamanho_kb < 100:
        problemas.append(f"PDF muito pequeno ({tamanho_kb:.0f} KB).")
    paginas = len(re.findall(rb"/Type\s*/Page[^s]", data))
    if paginas < 16:
        problemas.append(f"PDF com {paginas} paginas; esperado pelo menos 16.")
    print(f"PDF: {PDF_PATH.name} | {tamanho_kb:.0f} KB | {paginas} paginas")
    return problemas


def verificar_zip() -> list[str]:
    problemas: list[str] = []
    esperado = nome_esperado()
    zip_path = ZIP_DIR / esperado
    if not zip_path.exists():
        candidatos = sorted(ZIP_DIR.glob("*.zip")) if ZIP_DIR.exists() else []
        if not candidatos:
            return [f"ZIP nao encontrado em {ZIP_DIR} (esperado: {esperado})."]
        zip_path = candidatos[0]
        problemas.append(f"Nome do ZIP fora do padrao: {zip_path.name} (esperado: {esperado}).")

    with zipfile.ZipFile(zip_path) as archive:
        nomes = set(archive.namelist())
        for item in OBRIGATORIOS:
            if item not in nomes:
                problemas.append(f"Item obrigatorio ausente no ZIP: {item}")
        for nome in nomes:
            if _proibido(nome):
                problemas.append(f"Item que nao deveria estar no ZIP: {nome}")
        if not any(nome.startswith("docs/img/") for nome in nomes):
            problemas.append("Imagens da documentacao ausentes no ZIP.")
        tamanho_mb = zip_path.stat().st_size / (1024 * 1024)

    print(f"ZIP: {zip_path.name} | {tamanho_mb:.2f} MB | {len(nomes)} arquivos")
    return problemas


def main() -> int:
    print("Verificando pacote de entrega do Mente Saudavel...\n")
    problemas = verificar_pdf() + verificar_zip()
    if problemas:
        print("\nPendencias encontradas:")
        for problema in problemas:
            print(f"  - {problema}")
        return 1
    print("\nTudo certo: PDF e ZIP prontos para entrega.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
