"""
Filet CI : tout code de permission référencé par un décorateur @require_permission(...)
doit être injecté par tenxyte_seed (directement ou via un ancêtre hiérarchique).

Contexte : cf. specs/z_aud_0000/00.md. `audit.view` et `users.edit`/`users.update`
ont dérivé silencieusement entre les vues et le seed, rendant certains endpoints admin
inatteignables par tout le RBAC (y compris super_admin), sans qu'aucun test ne le détecte.
"""

import re
from pathlib import Path

import pytest

from tenxyte.management.commands.tenxyte_seed import DEFAULT_PERMISSIONS

SRC = Path(__file__).resolve().parent.parent / "src" / "tenxyte"
SEEDED = {p["code"] for p in DEFAULT_PERMISSIONS}
DECORATOR_RE = re.compile(
    r'@require_(?:any_|all_)?permissions?\(\s*(\[[^\]]*\]|["\'][^"\']*["\'])'
)


def _covered(code: str) -> bool:
    """Injecté directement, ou via un ancêtre injecté (hiérarchie)."""
    if code in SEEDED:
        return True
    parts = code.split(".")
    return any(".".join(parts[:i]) in SEEDED for i in range(1, len(parts)))


def _referenced_codes():
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for m in DECORATOR_RE.finditer(text):
            for code in re.findall(r'["\']([^"\']+)["\']', m.group(1)):
                yield code, path


@pytest.mark.parametrize(
    "code,path",
    sorted({(c, str(p)) for c, p in _referenced_codes()}),
)
def test_decorator_permission_is_seeded(code, path):
    assert _covered(code), (
        f"@require_permission({code!r}) dans {path} n'est ni dans "
        f"DEFAULT_PERMISSIONS ni couvert par un ancêtre injecté — "
        f"endpoint inatteignable par le RBAC."
    )
