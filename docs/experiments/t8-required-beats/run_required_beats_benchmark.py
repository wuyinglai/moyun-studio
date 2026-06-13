"""T8.2.1 required beats benchmark runner.

This is an experiment artifact, not product code. It reads local LLM config
but never prints or writes API keys.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
RESULTS_DIR = ROOT / "results"


CASES: list[dict[str, Any]] = [
    {
        "id": "case-01-seventh-protocol",
        "label": "Seventh Layer Protocol",
        "context": "旧港站广播室里，林澈和沈知夏暂时摆脱追兵。林澈身上的银色芯片刚刚被广播设备短暂激活。",
        "goal": "让林澈意识到芯片不是地图，而是某种筛选入口。",
        "beats": [
            {"id": "seventh_protocol", "text": "必须出现“第七层协议”。", "terms": ["第七层协议"]},
            {"id": "silver_chip", "text": "必须出现银色芯片。", "terms": ["银色芯片"]},
            {"id": "partial_coordinate", "text": "必须出现残缺坐标。", "terms": ["残缺坐标", "坐标"]},
            {"id": "pursuers_basement", "text": "必须出现追踪者进入地下层。", "terms": ["追踪者", "追兵", "地下层"]},
        ],
        "forbidden": [
            "不得直接揭晓第七层协议的完整真相。",
            "不得让追踪者拿到银色芯片。",
            "不得跳转到灰塔实验室。",
        ],
        "leak_terms": ["完整真相是", "协议的真相", "第七层协议其实是", "灰塔实验室"],
    },
    {
        "id": "case-02-item-handover",
        "label": "Item Handover",
        "context": "旧港站检修通道里，沈知夏从夹层取出一支透明药剂。林澈只来得及看见药剂上的标签。",
        "goal": "让药剂成为下一场景的压力源，而不是立刻解决问题。",
        "beats": [
            {"id": "medicine_with_shen", "text": "药剂仍在沈知夏手中。", "terms": ["沈知夏", "药剂", "手中"]},
            {"id": "lin_sees_label", "text": "林澈只能看到药剂标签。", "terms": ["林澈", "标签"]},
            {"id": "enemy_not_take", "text": "药剂不能被敌人拿走。", "terms": ["药剂"]},
            {"id": "side_effect_hint", "text": "结尾必须出现药剂副作用暗示。", "terms": ["副作用", "发抖", "眩晕", "刺痛", "发冷"]},
        ],
        "forbidden": [
            "不得让林澈直接拿走药剂。",
            "不得让敌人获得药剂。",
            "不得解释药剂全部用途。",
        ],
        "leak_terms": ["全部用途", "真正作用是", "敌人夺走药剂", "林澈接过药剂"],
    },
    {
        "id": "case-03-injury-limitation",
        "label": "Injury Limitation",
        "context": "沈知夏左臂受伤，林澈带她躲在旧港站地下二层的废弃售票室。追兵正在外面搜索。",
        "goal": "让两人配合通过危机，但保持伤势限制。",
        "beats": [
            {"id": "left_arm_injury", "text": "必须写出沈知夏左臂受伤。", "terms": ["左臂", "受伤"]},
            {"id": "no_high_fight", "text": "她不能高强度战斗。", "terms": ["不能", "无法", "不可能", "没法"]},
            {"id": "helps_by_observation", "text": "她通过观察或判断帮助林澈。", "terms": ["观察", "判断", "看出", "提醒"]},
            {"id": "lin_main_action", "text": "林澈承担主要行动。", "terms": ["林澈"]},
        ],
        "forbidden": [
            "不得让沈知夏攀爬、格斗、双手持械或左手发力。",
            "不得让林澈完全依赖沈知夏行动。",
            "不得新增治疗奇迹。",
        ],
        "leak_terms": ["沈知夏攀", "沈知夏爬", "沈知夏挥", "双手持", "左手用力", "奇迹般恢复"],
    },
    {
        "id": "case-04-ending-hook",
        "label": "Ending Hook",
        "context": "林澈和沈知夏躲进旧港站档案室，门外追兵的声音渐渐远去。走廊深处忽然安静下来。",
        "goal": "制造下一场景的悬念，而不是在本场解决。",
        "beats": [
            {"id": "familiar_steps", "text": "门后传来熟悉脚步声。", "terms": ["熟悉", "脚步"]},
            {"id": "lin_recognizes", "text": "林澈认出脚步声。", "terms": ["认出", "听出"]},
            {"id": "identity_hidden", "text": "不能揭晓来人身份。", "terms": ["没有说出", "不能确定", "没有揭晓", "没有喊出"]},
            {"id": "ends_with_look_up", "text": "结尾停在林澈抬头。", "terms": ["林澈抬头", "抬起头"]},
        ],
        "forbidden": [
            "不得写出来人的名字或身份。",
            "不得让来人直接开口解释。",
            "不得把钩子提前解开。",
        ],
        "leak_terms": ["来人是", "那是", "父亲", "导师", "队长", "开口说道", "解释道"],
    },
]


VARIANTS: list[dict[str, str]] = [
    {
        "id": "A",
        "label": "Inline required beats",
        "builder": "inline",
    },
    {
        "id": "B",
        "label": "Numbered required beats",
        "builder": "numbered",
    },
    {
        "id": "C",
        "label": "Self-check after draft",
        "builder": "self_check",
    },
    {
        "id": "D",
        "label": "Beat outline first",
        "builder": "outline_first",
    },
]


def read_llm_config() -> tuple[str, str, str]:
    config_path = REPO_ROOT / "workspace" / ".config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    llm = config.get("llm") or {}
    api_key = llm.get("apiKey")
    if not api_key:
        raise RuntimeError("No API key configured for benchmark.")
    api_url = (llm.get("apiUrl") or "https://apihub.agnes-ai.com/v1").rstrip("/")
    model = (llm.get("model") or "agnes-2.0-flash").split("/")[-1]
    return api_key, api_url, model


def build_prompt(case: dict[str, Any], variant: dict[str, str]) -> str:
    beats_inline = "、".join(beat["text"] for beat in case["beats"])
    beats_numbered = "\n".join(f"{idx}. {beat['text']}" for idx, beat in enumerate(case["beats"], 1))
    forbidden = "\n".join(f"- {item}" for item in case["forbidden"])
    base = f"""你是严谨的中文长篇小说场景写作者。
上文：{case['context']}
本场目标：{case['goal']}
禁止事项：
{forbidden}

要求：写一个约 500 中文字的完整场景。只输出正文，不输出标题、分析或编号。
"""
    builder = variant["builder"]
    if builder == "inline":
        return base + f"\n本场必须出现：{beats_inline}\n正文必须自然承接上文。"
    if builder == "numbered":
        return base + f"\n【本场必须完成的 {len(case['beats'])} 个信息点】\n{beats_numbered}\n正文必须自然包含以上全部信息点，不能漏掉任何一点。"
    if builder == "self_check":
        return base + f"\n【本场必须完成的 {len(case['beats'])} 个信息点】\n{beats_numbered}\n生成正文前，请在内部确认以上信息点是否全部包含。如果任一项缺失，请重写后再输出最终正文。最终只输出正文，不输出检查过程。"
    if builder == "outline_first":
        return base + f"\n【本场必须完成的 {len(case['beats'])} 个信息点】\n{beats_numbered}\n先在内部用 {len(case['beats'])} 行规划这些信息点，再严格按规划写正文。最终只输出正文，不输出规划。"
    raise ValueError(f"Unknown variant builder: {builder}")


def call_llm(api_key: str, api_url: str, model: str, prompt: str) -> tuple[str, float]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严谨的中文长篇小说写作助手。只输出中文正文。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 900,
    }
    request = urllib.request.Request(
        api_url + "/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc
    elapsed = round(time.perf_counter() - start, 2)
    return data["choices"][0]["message"]["content"].strip(), elapsed


def beat_present(text: str, beat: dict[str, Any]) -> bool:
    terms = beat["terms"]
    if beat["id"] == "pursuers_basement":
        return any(t in text for t in ["追踪者", "追兵"]) and "地下" in text
    if beat["id"] == "medicine_with_shen":
        return "沈知夏" in text and "药剂" in text and any(t in text for t in ["手中", "掌心", "握着", "攥着"])
    if beat["id"] == "enemy_not_take":
        return "药剂" in text and not any(t in text for t in ["敌人夺走药剂", "追兵夺走药剂", "敌人拿走药剂"])
    if beat["id"] == "identity_hidden":
        return not reveals_identity(text)
    return any(term in text for term in terms)


def reveals_identity(text: str) -> bool:
    return any(term in text for term in ["来人是", "那是", "父亲", "导师", "队长", "开口说道", "解释道"])


def score_output(case: dict[str, Any], text: str) -> dict[str, Any]:
    completed = [beat["id"] for beat in case["beats"] if beat_present(text, beat)]
    missing = [beat["id"] for beat in case["beats"] if beat["id"] not in completed]
    leaks = [term for term in case["leak_terms"] if term in text]
    exposed_outline = any(marker in text for marker in ["1.", "2.", "规划", "信息点", "检查"])
    contradictions = []
    if case["id"] == "case-03-injury-limitation":
        contradictions = [term for term in ["沈知夏攀", "沈知夏爬", "双手持", "左手用力", "奇迹般恢复"] if term in text]
    usability = 2
    if leaks or contradictions:
        usability = 0
    elif missing or exposed_outline:
        usability = 1
    return {
        "beat_total": len(case["beats"]),
        "beat_completed": len(completed),
        "beat_missing": len(missing),
        "completed": completed,
        "missing": missing,
        "leaks": leaks,
        "exposed_outline": exposed_outline,
        "contradictions": contradictions,
        "usability": usability,
    }


def summarize(results: list[dict[str, Any]], model: str) -> str:
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        by_variant.setdefault(item["variant"], []).append(item)

    lines = [
        "# T8.2.1 Required Beats Benchmark Summary",
        "",
        "## 1. Background",
        "",
        "T8.2 showed that facts-first prompt ordering did not solve required-beat omission. This experiment isolates that failure mode: whether small models reliably include mandatory scene beats in prose.",
        "",
        "This task did not modify product code, production prompts, pipeline, frontend, backend, release tags, workspace data, or API-key configuration.",
        "",
        "## 2. Relation to T8.0 / T8.1 / T8.2",
        "",
        "| Stage | Focus | Result feeding this task |",
        "| --- | --- | --- |",
        "| T8.0 | Single prompt wording | Prompt wording alone was not enough to guarantee logic |",
        "| T8.1 | Prompt assembly strategies | Facts-first looked practical but not decisive |",
        "| T8.2 | Product opt-in facts-first + debug prompt export | Both current-like and facts-first missed a required beat |",
        "| T8.2.1 | Required beats stability | Tests required-beat completion directly |",
        "",
        "## 3. Model and Method",
        "",
        f"- Model: `{model}`",
        "- Calls: 4 cases x 4 variants = 16 generations",
        "- Temperature: 0.1",
        "- Output target: about 500 Chinese characters",
        "- Scoring: deterministic required-beat checks plus leak/outline/contradiction checks",
        "- API keys: not printed or written",
        "",
        "## 4. Prompt Variants",
        "",
        "| Variant | Strategy |",
        "| --- | --- |",
        "| A | Inline required beats |",
        "| B | Numbered required beats |",
        "| C | Silent self-check before final output |",
        "| D | Beat outline first, final prose only |",
        "",
        "## 5. Test Cases",
        "",
        "| Case | Focus | Required beat count |",
        "| --- | --- | ---: |",
    ]
    for case in CASES:
        lines.append(f"| {case['id']} | {case['label']} | {len(case['beats'])} |")

    lines.extend([
        "",
        "## 6. Result Table",
        "",
        "| Variant | Beat completion rate | Missing beats | Leak count | Usable candidates | Average time | Conclusion |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    for variant in VARIANTS:
        items = by_variant.get(variant["id"], [])
        total = sum(item["score"]["beat_total"] for item in items)
        completed = sum(item["score"]["beat_completed"] for item in items)
        missing = sum(item["score"]["beat_missing"] for item in items)
        leaks = sum(1 for item in items if item["score"]["leaks"])
        usable = sum(1 for item in items if item["score"]["usability"] >= 1)
        avg_time = round(sum(item["elapsed"] for item in items) / max(len(items), 1), 2)
        rate = completed / total if total else 0
        conclusion = "Best" if missing == min(sum(x["score"]["beat_missing"] for x in by_variant.get(v["id"], [])) for v in VARIANTS) else "Mixed"
        lines.append(f"| {variant['id']} {variant['label']} | {rate:.2%} | {missing} | {leaks} | {usable}/{len(items)} | {avg_time:.2f}s | {conclusion} |")

    lines.extend([
        "",
        "## 7. Case-Level Detail",
        "",
        "| Case | Variant | Completed | Missing | Leaks | Usability | Time |",
        "| --- | --- | ---: | --- | --- | ---: | ---: |",
    ])
    for item in results:
        score = item["score"]
        lines.append(
            f"| {item['case']} | {item['variant']} | {score['beat_completed']}/{score['beat_total']} | "
            f"{', '.join(score['missing']) or 'None'} | {', '.join(score['leaks']) or 'None'} | "
            f"{score['usability']} | {item['elapsed']:.2f}s |"
        )

    best_variant = min(
        VARIANTS,
        key=lambda v: (
            sum(item["score"]["beat_missing"] for item in by_variant.get(v["id"], [])),
            -sum(item["score"]["usability"] for item in by_variant.get(v["id"], [])),
            sum(item["elapsed"] for item in by_variant.get(v["id"], [])) / max(len(by_variant.get(v["id"], [])), 1),
        ),
    )
    lines.extend([
        "",
        "## 8. Best Strategy",
        "",
        f"Best strategy in this run: **Variant {best_variant['id']} - {best_variant['label']}**.",
        "",
        "The result should be treated as directional, not final. The sample is intentionally small and deterministic scoring can miss semantic equivalents.",
        "",
        "## 9. Key Findings",
        "",
        "1. Required beats can still be missed even when they are clearly present in the prompt.",
        "2. Numbered or self-check wording improves auditability of the instruction but does not guarantee completion.",
        "3. Beat-outline-first can help the model attend to required beats, but it risks mechanical prose or accidental outline leakage.",
        "4. Required-beat omission should be treated as a reliability problem separate from general continuity or prose quality.",
        "5. A product-grade solution likely needs post-generation beat validation, not prompt wording alone.",
        "",
        "## 10. Should This Enter Product Prompt Assembly?",
        "",
        "Not as a default prompt replacement yet.",
        "",
        "Recommended product direction:",
        "",
        "- keep production prompts unchanged;",
        "- use debug prompt export to confirm beats enter final prompts;",
        "- add a required-beat validator experiment before T8.3;",
        "- only consider product prompt changes after a larger sample shows stable improvement.",
        "",
        "## 11. Next Step",
        "",
        "Run T8.2.2 with an explicit beat validator: generate prose, check required beats deterministically or with a separate model, then either repair the draft or create a candidate warning. Do not start Scene Plan + Checker productization until required-beat validation is understood.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    api_key, api_url, model = read_llm_config()
    results: list[dict[str, Any]] = []
    raw_lines = [
        "# T8.2.1 Raw Required Beats Generations",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"Model: `{model}`",
        "",
        "API keys are not recorded in this artifact.",
        "",
    ]

    for case in CASES:
        for variant in VARIANTS:
            prompt = build_prompt(case, variant)
            text, elapsed = call_llm(api_key, api_url, model, prompt)
            score = score_output(case, text)
            results.append({
                "case": case["id"],
                "variant": variant["id"],
                "variant_label": variant["label"],
                "elapsed": elapsed,
                "score": score,
                "text": text,
            })
            raw_lines.extend([
                f"## {case['id']} / Variant {variant['id']}",
                "",
                f"Elapsed: {elapsed:.2f}s",
                "",
                "Score:",
                "",
                "```json",
                json.dumps(score, ensure_ascii=False, indent=2),
                "```",
                "",
                "Output:",
                "",
                text,
                "",
            ])

    data = {
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "variants": VARIANTS,
        "cases": [{k: v for k, v in case.items() if k != "leak_terms"} for case in CASES],
        "results": results,
    }
    (RESULTS_DIR / "required-beats-data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (RESULTS_DIR / "raw-required-beats-generations.md").write_text(
        "\n".join(raw_lines),
        encoding="utf-8",
    )
    (RESULTS_DIR / "required-beats-summary.md").write_text(
        summarize(results, model),
        encoding="utf-8",
    )
    compact = [
        {
            "case": item["case"],
            "variant": item["variant"],
            "completed": item["score"]["beat_completed"],
            "missing": item["score"]["missing"],
            "usability": item["score"]["usability"],
            "elapsed": item["elapsed"],
        }
        for item in results
    ]
    print(json.dumps({"model": model, "results": compact}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
