from __future__ import annotations

from .models import BenchmarkItem


CONDITIONS = {
    "direct_tajik",
    "tajik_matched_control",
    "tajik_reasoning",
    "pivot_english",
    "pivot_russian",
    "pivot_persian",
    "translation_only_english",
    "translation_only_russian",
    "translation_only_persian",
}


def task_text(item: BenchmarkItem) -> str:
    if item.category == "grammar":
        return (
            f"{item.prompt_tg}\nA: {item.option_a}\nB: {item.option_b}\n"
            "Танҳо A ё B ҷавоб диҳед."
        )
    return item.prompt_tg


def render_prompt(item: BenchmarkItem, condition: str) -> str:
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown prompt condition: {condition}")
    task = task_text(item)
    instructions = {
        "direct_tajik": "Ба супориш мустақиман ба забони тоҷикӣ ҷавоб диҳед.",
        "tajik_matched_control": "Супоришро бодиққат ба забони тоҷикӣ хонед, онро ба тоҷикӣ ҳал кунед ва танҳо ҷавоби ниҳоиро ба тоҷикӣ диҳед. Раванди мулоҳизаро нишон надиҳед.",
        "tajik_reasoning": "Супоришро бодиққат ба забони тоҷикӣ таҳлил кунед ва танҳо ҷавоби ниҳоиро ба тоҷикӣ диҳед.",
        "pivot_english": "Interpret the task in English, solve it, and return only the final answer in Tajik. Do not reveal hidden reasoning.",
        "pivot_russian": "Интерпретируйте задание по-русски, решите его и верните только окончательный ответ на таджикском. Не раскрывайте скрытые рассуждения.",
        "pivot_persian": "دستور را به فارسی تفسیر و حل کنید، سپس فقط پاسخ نهایی را به تاجیکی با خط سیریلیک ارائه دهید. استدلال پنهان را نمایش ندهید.",
        "translation_only_english": "Матнро ба англисӣ ва сипас ба тоҷикӣ бозтарҷума кунед. Ба супориш ҷавоб надиҳед; танҳо матни бозтарҷумашударо диҳед.",
        "translation_only_russian": "Матнро ба русӣ ва сипас ба тоҷикӣ бозтарҷума кунед. Ба супориш ҷавоб надиҳед; танҳо матни бозтарҷумашударо диҳед.",
        "translation_only_persian": "Матнро ба форсӣ ва сипас ба тоҷикӣ бозтарҷума кунед. Ба супориш ҷавоб надиҳед; танҳо матни бозтарҷумашударо диҳед.",
    }
    return f"{instructions[condition]}\n\nСупориш:\n{task}"
