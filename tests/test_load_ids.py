from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import load_notification_ids


def test_load_notification_ids_strips_blanks_and_duplicates(tmp_path: Path) -> None:
    ids_file = tmp_path / "ids.txt"
    ids_file.write_text(" 100 \n\n200\n100\n 300\n", encoding="utf-8")

    assert load_notification_ids(ids_file) == ["100", "200", "300"]


def test_load_notification_ids_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"

    try:
        load_notification_ids(missing)
    except FileNotFoundError as error:
        assert "Arquivo de IDs não encontrado" in str(error)
    else:
        raise AssertionError("Era esperado FileNotFoundError")
