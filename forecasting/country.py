"""Normalize messy company country strings to ISO-2. Never infer from currency, id, or name."""
import json
from pathlib import Path

_ALIASES = json.loads(
    (Path(__file__).resolve().parent / 'datasets' / 'external' / 'country_aliases.json').read_text(encoding='utf-8')
)
_FOLD = {key.casefold(): code for key, code in _ALIASES.items()}
_UPPER = {key.upper(): code for key, code in _ALIASES.items()}


def normalize_country(value) -> str:
    if value is None:
        return ''
    text = str(value).strip()
    if not text:
        return ''
    return _ALIASES.get(text) or _FOLD.get(text.casefold()) or _UPPER.get(text.upper()) or ''


def known_country(value) -> bool:
    return bool(normalize_country(value))
