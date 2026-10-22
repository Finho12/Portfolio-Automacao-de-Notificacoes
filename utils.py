from pathlib import Path


def load_notification_ids(path: Path) -> list[str]:
    """Lê IDs únicos, não vazios, mantendo a ordem original."""
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de IDs não encontrado: {path}")
    ids = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return list(dict.fromkeys(value for value in ids if value))
