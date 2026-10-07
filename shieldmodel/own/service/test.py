"""
Тестовый прогон OwnSpamClassifier на каверзном датасете.

Запуск:
    python -m moderation.tests.test_own_model
или
    python moderation/tests/test_own_model.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# --- путь к проекту, чтобы импорт работал при прямом запуске ---
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ....app.services.own_model import OwnSpamClassifier  # noqa: E402


DATA_DIR = Path(__file__).resolve().parents[1] 
TEST_FILE = DATA_DIR / "service" / "test.jsonl"
MODEL_DIR ="./workers/ads_worker/app/shieldmodel/own"


# ------------------------------------------------------------------ loading

def load_jsonl(path: Path) -> List[dict]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"⚠️  Строка {i} в {path.name}: битый JSON — {e}")
    return items


# ------------------------------------------------------------------ colors

class C:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    END = "\033[0m"


def colored(text: str, color: str) -> str:
    return f"{color}{text}{C.END}"


# ------------------------------------------------------------------ test run

def run_test(clf: OwnSpamClassifier, dataset: List[dict]) -> Dict:
    """Прогоняет модель по датасету, печатает по каждому примеру,
    возвращает агрегированную статистику."""
    stats = {
        "total": 0,
        "tp": 0, "tn": 0, "fp": 0, "fn": 0,
        "by_category": defaultdict(lambda: {"total": 0, "correct": 0, "errors": []}),
        "errors": [],
    }

    for ex in dataset:
        text = ex["text"]
        expected = ex["label"]
        category = ex.get("category", "unknown")

        pred = clf.predict(text)
        got = 1 if pred.is_spam else 0
        correct = got == expected

        stats["total"] += 1
        stats["by_category"][category]["total"] += 1
        if correct:
            stats["by_category"][category]["correct"] += 1

        if expected == 1 and got == 1:
            stats["tp"] += 1
        elif expected == 0 and got == 0:
            stats["tn"] += 1
        elif expected == 0 and got == 1:
            stats["fp"] += 1
            stats["errors"].append(("FP", category, text, pred))
            stats["by_category"][category]["errors"].append(("FP", text, pred))
        else:
            stats["fn"] += 1
            stats["errors"].append(("FN", category, text, pred))
            stats["by_category"][category]["errors"].append(("FN", text, pred))

        # короткая строка по каждому примеру
        mark = colored("✓", C.GREEN) if correct else colored("✗", C.RED)
        exp_s = "spam" if expected == 1 else "ok"
        got_s = "spam" if got == 1 else "ok"
        print(
            f"{mark} [{category:>20}] "
            f"expected={exp_s:>4} got={got_s:>4} "
            f"conf={pred.confidence:.2f} proba={pred.proba:.2f} "
            f"reason={pred.reason} "
            f"| {text[:70]}"
        )

    return stats


# ------------------------------------------------------------------ report

def print_report(stats: Dict) -> None:
    total = stats["total"]
    tp, tn, fp, fn = stats["tp"], stats["tn"], stats["fp"], stats["fn"]

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / total if total else 0.0

    print()
    print(colored("=" * 70, C.CYAN))
    print(colored("ОБЩИЕ МЕТРИКИ", C.BOLD))
    print(colored("=" * 70, C.CYAN))
    print(f"Всего примеров: {total}")
    print(f"  TP (спам пойман):        {tp}")
    print(f"  TN (safe пропущен):      {tn}")
    print(f"  FP (safe назван спамом): {colored(str(fp), C.YELLOW)}")
    print(f"  FN (спам пропущен):      {colored(str(fn), C.RED)}")
    print()
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")
    print(f"  F1:        {f1:.3f}")
    print(f"  Accuracy:  {accuracy:.3f}")

    print()
    print(colored("=" * 70, C.CYAN))
    print(colored("ПО КАТЕГОРИЯМ", C.BOLD))
    print(colored("=" * 70, C.CYAN))
    for cat, s in sorted(stats["by_category"].items()):
        acc = s["correct"] / s["total"] if s["total"] else 0
        color = C.GREEN if acc == 1.0 else (C.YELLOW if acc >= 0.5 else C.RED)
        print(f"  {cat:>22}: {s['correct']}/{s['total']} ({acc:.0%})")
        # показываем ошибки внутри категории
        for kind, text, pred in s["errors"]:
            kind_c = C.YELLOW if kind == "FP" else C.RED
            print(
                f"      {colored(kind, kind_c)} "
                f"conf={pred.confidence:.2f} proba={pred.proba:.2f} "
                f"| {text[:60]}"
            )

    # короткий список самых проблемных
    print()
    print(colored("=" * 70, C.CYAN))
    print(colored("ХУДШИЕ КАТЕГОРИИ", C.BOLD))
    print(colored("=" * 70, C.CYAN))
    worst = sorted(
        stats["by_category"].items(),
        key=lambda kv: kv[1]["correct"] / kv[1]["total"] if kv[1]["total"] else 1,
    )[:5]
    for cat, s in worst:
        acc = s["correct"] / s["total"] if s["total"] else 0
        print(f"  {cat:>22}: {acc:.0%} ({s['correct']}/{s['total']})")


# ------------------------------------------------------------------ main

def main():
    if not TEST_FILE.exists():
        print(colored(f"❌ Не найден {TEST_FILE}", C.RED))
        return 1

    print(colored(f"Загрузка датасета: {TEST_FILE}", C.CYAN))
    dataset = load_jsonl(TEST_FILE)
    print(f"Примеров: {len(dataset)}")

    print(colored(f"Загрузка модели: {MODEL_DIR}", C.CYAN))
    clf = OwnSpamClassifier(model_dir=str(MODEL_DIR))
    loaded = clf.load()
    if not loaded:
        print(colored(
            "⚠️  Модель не загружена. predict вернёт reason='own_model_untrained'.",
            C.YELLOW,
        ))
        print(colored(
            "    Сначала обучи модель на starter_dataset.jsonl.",
            C.YELLOW,
        ))

    if clf.clf is not None:
        print(f"Модель: n_features_in_={clf.clf.n_features_in_}, "
              f"n_total={clf.n_total}, n_pos={clf.n_pos}")
    print()

    stats = run_test(clf, dataset)
    print_report(stats)

    # exit code: 0 если precision>=0.7 и recall>=0.7, иначе 1
    tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision >= 0.7 and recall >= 0.7:
        print(colored("\n✅ Модель проходит порог precision>=0.7, recall>=0.7", C.GREEN))
        return 0
    print(colored(
        f"\n❌ Модель не проходит порог: precision={precision:.2f}, recall={recall:.2f}",
        C.RED,
    ))
    return 1


if __name__ == "__main__":
    sys.exit(main())