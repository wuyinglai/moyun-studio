# T8.0 prompt benchmark runner.
#
# This script is intentionally placed under docs/experiments because it is an
# experiment artifact, not product code. It reads the local Moyun LLM config but
# never prints or writes API keys.

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
RESULTS_DIR = ROOT / "results"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(markdown: str, title: str) -> str:
    match = re.search(rf"## {re.escape(title)}\n\n(.*?)(?=\n## |\Z)", markdown, re.S)
    return match.group(1).strip() if match else ""


def list_section(markdown: str, title: str) -> str:
    return "\n".join(line.strip() for line in section(markdown, title).splitlines() if line.strip())


def fill_template(template: str, **kwargs: str) -> str:
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", value)
    return template.replace("700-900", "500-700")


def load_llm_config() -> tuple[str, str, str]:
    config_path = REPO_ROOT / "workspace" / ".config.json"
    config = json.loads(read_text(config_path))
    llm = config.get("llm") or {}
    api_key = llm.get("apiKey")
    if not api_key:
        raise RuntimeError("No API key configured for benchmark.")
    api_url = (llm.get("apiUrl") or "https://apihub.agnes-ai.com/v1").rstrip("/")
    model = (llm.get("model") or "agnes-2.0-flash").split("/")[-1]
    return api_key, api_url, model


def call_llm(api_key: str, api_url: str, model: str, prompt: str, max_tokens: int = 1000) -> tuple[str, float]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严谨的中文长篇小说写作助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
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


def score_case(case_id: str, text: str) -> tuple[dict[str, int], list[str]]:
    score = {
        "character_state": 2,
        "item_ownership": 2,
        "timeline": 2,
        "location": 2,
        "forbidden": 2,
        "scene_goal": 2,
        "foreshadowing": 2,
        "contradiction_count": 2,
        "usability": 2,
    }
    errors: list[str] = []

    def fail(metric: str, reason: str, hard: bool = False) -> None:
        score[metric] = min(score[metric], 0 if hard else 1)
        errors.append(reason)

    if case_id == "case-01-injury-state":
        if any(word in text for word in ["攀上", "攀住", "攀爬", "挥拳", "格斗", "双手持枪", "飞奔", "狂奔"]):
            fail("character_state", "可能让沈知夏做高强度动作", True)
        if any(word in text for word in ["左手死死", "左手紧紧", "左手抓", "左手扣", "左手用力", "左臂肌肉紧绷"]):
            fail("character_state", "沈知夏左手/左臂被写成可发力状态", True)
        if "右肩" in text or "右臂" in text:
            fail("character_state", "受伤部位从左臂漂移到右肩/右臂", True)
        if any(word in text for word in ["敌人手里的银色芯片", "追兵拿着银色芯片", "芯片落到追兵"]):
            fail("item_ownership", "银色芯片归属疑似错乱", True)
        if any(word in text for word in ["灰塔实验室", "地面广场", "城北"]):
            fail("location", "地点可能跳出旧港站地下", True)
        if "扫描" not in text and "光" not in text:
            fail("scene_goal", "未体现扫描光异常")
    elif case_id == "case-02-item-ownership":
        if any(word in text for word in ["沈知夏掏出芯片", "沈知夏拿出芯片", "敌人拿出芯片", "追兵手中那枚芯片"]):
            fail("item_ownership", "芯片持有人错误", True)
        if any(word in text for word in ["完整用途", "真正用途是", "全部解码", "破解完成"]):
            fail("foreshadowing", "芯片用途揭晓过度", True)
        if "编号" in text and any(word in text for word in ["追兵报出", "敌人说出编号"]):
            fail("forbidden", "追兵知道不该知道的编号", True)
    elif case_id == "case-03-timeline":
        if any(word in text for word in ["爆炸已经", "爆炸发生", "火光吞没", "第三天清晨的门禁记录", "拿到了门禁记录"]):
            fail("timeline", "未来事件或证据提前出现", True)
        if any(word in text for word in ["旧港站会发生爆炸", "档案里写得清清楚楚"]):
            fail("forbidden", "角色知道的信息过于确定")
        if any(word in text for word in ["爆炸原因是", "真正原因就是"]):
            fail("forbidden", "提前知道爆炸原因")
        if not any(word in text for word in ["第三天", "时间", "证据", "夜里"]):
            fail("scene_goal", "未推进时间点证据目标")
    elif case_id == "case-04-location":
        if any(word in text for word in ["灰塔实验室里", "抵达灰塔", "来到灰塔", "外面的电话", "联系上", "直达实验室的密道"]):
            fail("location", "地点/通讯/密道限制被破坏", True)
        if not any(word in text for word in ["维修图", "控制室", "设备往来", "月台"]):
            fail("scene_goal", "未完成维修图目标")
    elif case_id == "case-05-no-new-entities":
        if any(word in text for word in ["神秘老人", "导师", "黑客", "盟友", "新组织", "暗鸦", "第九局", "系统提示", "异能"]):
            fail("forbidden", "新增了禁止实体或设定", True)
        if not any(word in text for word in ["广播", "误导", "追兵", "控制室"]):
            fail("scene_goal", "未完成广播误导目标")
    elif case_id == "case-06-foreshadowing-relationship-style":
        if any(word in text for word in ["我爱你", "完全相信你", "毫无保留地信任", "深情"]):
            fail("character_state", "关系进展过快", True)
        if any(word in text for word in ["第七层协议的全部真相", "筛选对象是", "完整真相是"]):
            fail("foreshadowing", "伏笔提前揭晓", True)
        if any(word in text for word in ["筛选的是人性", "筛选的是人", "筛选的是变量", "成为新的标准"]):
            fail("foreshadowing", "第七层协议的筛选对象/含义揭示过多", True)
        if any(word in text for word in ["打脸", "热血沸腾", "哈哈", "段子", "爽到"]):
            fail("forbidden", "风格跑偏")
        if "筛选方式" not in text:
            fail("scene_goal", "未给出有限线索")

    if len(text) < 180:
        fail("usability", "正文过短")
    if len(text) > 1800:
        fail("usability", "正文过长")

    hard_failures = sum(1 for value in score.values() if value == 0)
    if hard_failures >= 2:
        score["contradiction_count"] = 0
        score["usability"] = min(score["usability"], 1)
    elif errors:
        score["contradiction_count"] = min(score["contradiction_count"], 1)

    return score, errors


def aggregate(records: list[dict]) -> dict[str, dict[str, float]]:
    groups: dict[str, dict[str, float]] = defaultdict(lambda: {"total": 0, "n": 0, "errors": 0, "usable": 0, "contradiction_cases": 0, "elapsed": 0})
    for record in records:
        group = groups[record["variant"]]
        group["total"] += record["total"]
        group["n"] += 1
        group["errors"] += len(record["errors"])
        group["elapsed"] += record["elapsed_seconds"]
        if record["score"]["usability"] >= 2 and record["total"] >= 16:
            group["usable"] += 1
        if record["score"]["contradiction_count"] < 2:
            group["contradiction_cases"] += 1
    for group in groups.values():
        group["average"] = round(group["total"] / max(group["n"], 1), 2)
        group["average_elapsed"] = round(group["elapsed"] / max(group["n"], 1), 2)
    return dict(groups)


def main() -> None:
    os.environ.setdefault("HTTP_PROXY", "http://127.0.0.1:7897")
    os.environ.setdefault("HTTPS_PROXY", "http://127.0.0.1:7897")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    api_key, api_url, model = load_llm_config()
    prompt_a = read_text(ROOT / "prompts" / "prompt-a-direct.md")
    prompt_b = read_text(ROOT / "prompts" / "prompt-b-hard-constraints.md")
    prompt_c = read_text(ROOT / "prompts" / "prompt-c-scene-plan.md")
    prompt_c1 = prompt_c.split("## C2: Draft From Plan Prompt")[0]
    prompt_c2 = "## C2: Draft From Plan Prompt" + prompt_c.split("## C2: Draft From Plan Prompt", 1)[1]

    records: list[dict] = []
    raw_lines = [
        "# T8 Prompt Benchmark Raw Generations\n\n",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}\n",
        f"- model: {model}\n",
        "- API key: not recorded\n",
        "- proxy: 127.0.0.1:7897 used if available\n",
    ]

    for case_file in sorted((ROOT / "cases").glob("case-*.md")):
        case_id = case_file.stem
        case_text = read_text(case_file)
        fields = {
            "context": section(case_text, "上文摘要"),
            "facts": list_section(case_text, "必须保持的事实") or list_section(case_text, "必须遵守的事实"),
            "forbidden": list_section(case_text, "禁止改变的事实"),
            "goal": section(case_text, "本场生成目标"),
            "risks": list_section(case_text, "预期风险点"),
        }
        if not fields["context"] or not fields["goal"]:
            raise RuntimeError(f"Failed to parse benchmark case: {case_file}")

        for variant, template in [("A", prompt_a), ("B", prompt_b)]:
            text, elapsed = call_llm(api_key, api_url, model, fill_template(template, **fields))
            score, errors = score_case(case_id, text)
            records.append(
                {
                    "case": case_id,
                    "variant": variant,
                    "model": model,
                    "elapsed_seconds": elapsed,
                    "score": score,
                    "total": sum(score.values()),
                    "errors": errors,
                    "text": text,
                }
            )
            raw_lines.extend(
                [
                    f"\n## {case_id} / Prompt {variant}\n\n",
                    f"- elapsed_seconds: {elapsed}\n",
                    f"- score_total: {sum(score.values())}\n",
                    f"- errors: {errors or []}\n\n",
                    text,
                    "\n",
                ]
            )
            print(case_id, variant, sum(score.values()), elapsed)

        plan, plan_elapsed = call_llm(api_key, api_url, model, fill_template(prompt_c1, **fields), max_tokens=700)
        draft, draft_elapsed = call_llm(api_key, api_url, model, fill_template(prompt_c2, plan=plan, **fields))
        score, errors = score_case(case_id, draft)
        records.append(
            {
                "case": case_id,
                "variant": "C",
                "model": model,
                "elapsed_seconds": round(plan_elapsed + draft_elapsed, 2),
                "plan_elapsed_seconds": plan_elapsed,
                "draft_elapsed_seconds": draft_elapsed,
                "plan": plan,
                "score": score,
                "total": sum(score.values()),
                "errors": errors,
                "text": draft,
            }
        )
        raw_lines.extend(
            [
                f"\n## {case_id} / Prompt C\n\n",
                f"- plan_elapsed_seconds: {plan_elapsed}\n",
                f"- draft_elapsed_seconds: {draft_elapsed}\n",
                f"- score_total: {sum(score.values())}\n",
                f"- errors: {errors or []}\n\n",
                "### Plan\n\n",
                plan,
                "\n\n### Draft\n\n",
                draft,
                "\n",
            ]
        )
        print(case_id, "C", sum(score.values()), round(plan_elapsed + draft_elapsed, 2))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "api_base": api_url,
        "records": records,
        "aggregate": aggregate(records),
    }
    (RESULTS_DIR / "benchmark-data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS_DIR / "raw-generations.md").write_text("".join(raw_lines), encoding="utf-8")
    print("DONE records", len(records))


if __name__ == "__main__":
    main()
