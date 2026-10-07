# moderation/normalize.py
"""Нормализация текста для антиспам-моделей.

ВАЖНО:
- normalize() — только для подачи в векторайзер. Сохраняет читаемость,
  но не стирает spaced-letters (это сигнал бота, его ловят meta-фичи).
- compact() — сжатая форма для fuzzy-поиска ключевых слов в manual_features.
"""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------- tables

CYR2LAT = {
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y',
    'х': 'x', 'к': 'k', 'в': 'b', 'н': 'h', 'м': 'm', 'т': 't',
}
LEET = {
    '0': 'о', '1': 'и', '3': 'е', '4': 'а', '5': 's',
    '6': 'b', '7': 't', '8': 'b', '9': 'g', '$': 's', '@': 'a',
}
TRANS = str.maketrans({**CYR2LAT, **LEET})

# бренды с настоящими цифрами/латиницей — не трогаем при замене
BRANDS = (
    "1win", "1xbet", "1xstavka", "1xgames",
    "csgo500", "csgoempire", "csgo", "cs2", "dota2", "dota",
)

# ---------------------------------------------------------------- regex

_ZW = re.compile(r'[\u200b-\u200f\u2060\ufeff]')
_ZW_INSIDE = re.compile(r'\w[\u200b-\u200f\u2060\ufeff]\w')
_SPACED_RUN = re.compile(r'(?:\b\w\b\s+){3,}\b\w\b')
_INNER_SEP = re.compile(r'(?<=\w)[^\w\s](?=\w)')
_REPEAT = re.compile(r'(.)\1{2,}')
_WS = re.compile(r'\s+')
_NONWORD = re.compile(r'[^\w\s]')

# ---------------------------------------------------------------- public


def normalize(text: str) -> str:
    """Основная нормализация для подачи в TF-IDF.

    - NFKC, lower
    - удаляем zero-width
    - хомоглифы cyr->lat, leet -> буквы (кроме брендов)
    - убираем разделители ВНУТРИ слов: к*зино -> кзино
    - схлопываем повторы 3+ -> 1
    - НЕ трогаем пробелы между буквами (spaced-letters остаются)
    """
    if not text:
        return ""

    t = unicodedata.normalize("NFKC", text).lower()
    t = _ZW.sub("", t)

    # защищаем бренды
    stash: dict[str, str] = {}
    for i, b in enumerate(BRANDS):
        if b in t:
            ph = f"\x00b{i}\x00"
            stash[ph] = b
            t = t.replace(b, ph)

    t = t.translate(TRANS)
    t = _INNER_SEP.sub("", t)
    t = _REPEAT.sub(r'\1', t)
    t = _WS.sub(" ", t).strip()

    for ph, b in stash.items():
        t = t.replace(ph, b)
    return t


def compact(text: str) -> str:
    """Сжатая форма для fuzzy-поиска ключевых слов.

    Убирает ВСЕ пробелы и пунктуацию, чтобы 'к а з и н о',
    'к*а*з*и*н*о', 'к-а-з-и-н-о' матчились на 'казино'.
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text).lower()
    t = _ZW.sub("", t)

    stash: dict[str, str] = {}
    for i, b in enumerate(BRANDS):
        if b in t:
            ph = f"\x00b{i}\x00"
            stash[ph] = b
            t = t.replace(b, ph)

    t = t.translate(TRANS)
    t = _NONWORD.sub("", t)   # всё, кроме букв/цифр/_ — вон
    t = _REPEAT.sub(r'\1', t)

    for ph, b in stash.items():
        t = t.replace(ph, b)
    return t


# ---------------------------------------------------------------- detectors


def has_spaced_letters(text: str) -> bool:
    """'н а ш е к а з и н о' — 4+ односложных токена подряд."""
    return bool(_SPACED_RUN.search(text))


def has_zw_inside_word(text: str) -> bool:
    """Zero-width ВНУТРИ слова (между словами — норма)."""
    return bool(_ZW_INSIDE.search(text))


def has_unicode_obfuscation(text: str) -> bool:
    """Есть ли хомоглифы (кир+лат в одном слове) или leet в кириллице."""
    words = re.findall(r'\w+', text.lower())
    if not words:
        return False
    lat = set("abcdefghijklmnopqrstuvwxyz")
    cyr = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
    leet = set("013456789@$")
    for w in words:
        hl = any(c in lat for c in w)
        hc = any(c in cyr for c in w)
        if hl and hc:
            return True
        if any(c in leet for c in w) and hc:
            return True
    return False


def obfuscation_ratio(text: str) -> float:
    """Доля слов с обфускацией (хомоглиф/leet). 0..1."""
    words = re.findall(r'\w+', text.lower())
    if not words:
        return 0.0
    lat = set("abcdefghijklmnopqrstuvwxyz")
    cyr = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
    leet = set("013456789@$")
    bad = 0
    for w in words:
        hl = any(c in lat for c in w)
        hc = any(c in cyr for c in w)
        has_leet = any(c in leet for c in w) and hc
        if (hl and hc) or has_leet:
            bad += 1
    return bad / len(words)