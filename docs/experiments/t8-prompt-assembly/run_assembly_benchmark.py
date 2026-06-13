# T8.1 prompt assembly benchmark runner.
#
# This is an experiment artifact, not product code. It reads the local Moyun
# LLM config but never prints or writes API keys.

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
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
RESULTS_DIR = ROOT / "results"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(markdown: str, title: str) -> str:
    match = re.search(rf"## {re.escape(title)}\n\n(.*?)(?=\n## |\Z)", markdown, re.S)
    return match.group(1).strip() if match else ""


def list_section(markdown: str, title: str) -> list[str]:
    raw = section(markdown, title)
    return [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]


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


def parse_case(path: Path) -> dict[str, Any]:
    text = read_text(path)
    facts = section(text, "事实块")
    forbidden = section(text, "禁止改变项")
    return {
        "case": path.stem,
        "context": section(text, "上文摘要"),
        "facts": facts,
        "forbidden": forbidden,
        "goal": section(text, "本场目标"),
        "risks": section(text, "预期风险点"),
        "evaluation": section(text, "评价指标"),
        "fact_lines": list_section(text, "事实块") + list_section(text, "禁止改变项"),
    }


def key_terms(case: dict[str, Any]) -> list[str]:
    mapping = {
        "case-01-injury-state": ["沈知夏", "左臂", "左手不能用力", "银色芯片", "旧港站地下", "扫描光"],
        "case-02-item-ownership": ["银色芯片", "林澈", "贴身内袋", "追兵", "编号", "芯片尚未"],
        "case-03-timeline": ["第二天傍晚", "第三天", "爆炸尚未发生", "门禁记录尚未取得", "事故"],
        "case-04-location": ["旧港站地下二层", "通讯中断", "灰塔实验室", "月台控制室", "维修图"],
        "case-05-no-new-entities": ["林澈", "沈知夏", "追兵小队", "广播设备", "不能新增"],
        "case-06-foreshadowing": ["林澈仍不完全信任", "第七层协议", "筛选方式", "不能说出筛选对象", "悬疑克制"],
    }
    return mapping.get(case["case"], [])


def retention(prompt: str, case: dict[str, Any]) -> dict[str, Any]:
    terms = key_terms(case)
    present = [term for term in terms if term in prompt]
    missing = [term for term in terms if term not in prompt]
    return {
        "terms": terms,
        "present": present,
        "missing": missing,
        "ratio": round(len(present) / max(len(terms), 1), 2),
    }


def continuity_anchors(context: str) -> str:
    anchors = []
    for term in ["林澈", "沈知夏", "旧港站", "灰塔实验室", "银色芯片", "追兵", "第七层协议", "月台控制室"]:
        if term in context and term not in anchors:
            anchors.append(term)
    return "、".join(anchors)


def assembly_a(case: dict[str, Any]) -> str:
    return f"""【任务说明】
你是一名资深小说场景写作者。当前 sec 文件表示一个完整场景。
请写下一场景正文，约 500-700 中文字，只输出正文。

【上文 / 当前承接上下文】
{case['context']}

【continuity anchors】
{continuity_anchors(case['context'])}

【用户操作】
写下一场景。

【本场目标】
{case['goal']}

【参考信息】
故事状态 / 文风 / 近期上下文：
{case['facts']}

【禁止改变项】
{case['forbidden']}

【输出要求】
- 直接承接上文。
- 保留上文人物、地点、关键物件和悬念。
- 不要另起无关新故事。
- 不要输出标题、分析、编号或解释。"""


def assembly_b(case: dict[str, Any]) -> str:
    return f"""【任务】
写下一场景正文，约 500-700 中文字，只输出正文。

【不可违反事实】
{case['facts']}

【禁止事项】
{case['forbidden']}

【本场目标】
{case['goal']}

【参考上文】
{case['context']}

【输出要求】
- 用动作、环境、对话潜台词推进。
- 不要新增未允许的人物、组织、能力、道具、地点或关键设定。
- 不要提前揭晓伏笔。
- 不要解释自检过程。"""


def plan_prompt(case: dict[str, Any]) -> str:
    return f"""【任务】
根据事实块和上文，为下一场景生成 scene plan，不写正文。

【事实块】
{case['facts']}

【禁止改变项】
{case['forbidden']}

【本场目标】
{case['goal']}

【参考上文】
{case['context']}

【输出格式】
只输出 JSON，不要 Markdown：
{{
  "start_state": "...",
  "allowed_characters": ["..."],
  "allowed_locations": ["..."],
  "allowed_items": ["..."],
  "scene_goal": "...",
  "required_beats": ["..."],
  "forbidden_mistakes": ["..."],
  "ending_hook": "..."
}}"""


def checker_prompt(case: dict[str, Any], plan: str) -> str:
    return f"""【任务】
检查 scene plan 是否违反事实。只输出 JSON，不要 Markdown。

【事实块】
{case['facts']}

【禁止改变项】
{case['forbidden']}

【scene plan】
{plan}

【输出格式】
{{
  "valid": true,
  "issues": [],
  "risk_level": "low",
  "fix_suggestions": []
}}"""


def draft_prompt(case: dict[str, Any], plan: str, checker: str) -> str:
    return f"""【任务】
根据已检查的 scene plan 写下一场景正文，约 500-700 中文字。

【scene plan】
{plan}

【checker result】
{checker}

【参考上文】
{case['context']}

【硬性要求】
- 不得改变 scene plan 中的人物、地点、道具、时间线和禁令。
- 不得新增 scene plan 未允许的人物、组织、能力或关键设定。
- 只输出正文，不输出计划或解释。"""


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
    elif case_id == "case-06-foreshadowing":
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


def parse_checker(checker: str) -> dict[str, Any]:
    try:
        json_text = checker.strip()
        if "```" in json_text:
            match = re.search(r"```(?:json)?\s*(.*?)```", json_text, re.S)
            if match:
                json_text = match.group(1).strip()
        match = re.search(r"(\{.*\})", json_text, re.S)
        if match:
            json_text = match.group(1)
        parsed = json.loads(json_text)
        return {
            "parse_ok": True,
            "valid": bool(parsed.get("valid", False)),
            "issues_count": len(parsed.get("issues") or []),
            "risk_level": parsed.get("risk_level", "unknown"),
        }
    except Exception:
        return {"parse_ok": False, "valid": False, "issues_count": 0, "risk_level": "unknown"}


def aggregate(records: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    groups: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "total": 0,
            "n": 0,
            "errors": 0,
            "usable": 0,
            "contradiction_cases": 0,
            "elapsed": 0,
            "retention": 0,
            "checker_parse_ok": 0,
            "checker_issue_cases": 0,
        }
    )
    for record in records:
        group = groups[record["assembly"]]
        group["total"] += record["total"]
        group["n"] += 1
        group["errors"] += len(record["errors"])
        group["elapsed"] += record["elapsed_seconds"]
        group["retention"] += record["prompt_retention"]["ratio"]
        if record["score"]["usability"] >= 2 and record["total"] >= 16:
            group["usable"] += 1
        if record["score"]["contradiction_count"] < 2:
            group["contradiction_cases"] += 1
        checker = record.get("checker_summary") or {}
        if checker.get("parse_ok"):
            group["checker_parse_ok"] += 1
        if checker.get("issues_count", 0) > 0:
            group["checker_issue_cases"] += 1
    for group in groups.values():
        n = max(group["n"], 1)
        group["average"] = round(group["total"] / n, 2)
        group["average_elapsed"] = round(group["elapsed"] / n, 2)
        group["average_retention"] = round(group["retention"] / n, 2)
    return dict(groups)


def main() -> None:
    os.environ.setdefault("HTTP_PROXY", "http://127.0.0.1:7897")
    os.environ.setdefault("HTTPS_PROXY", "http://127.0.0.1:7897")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    api_key, api_url, model = load_llm_config()
    records: list[dict[str, Any]] = []
    raw_lines = [
        "# T8.1 Prompt Assembly Raw Generations\n\n",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}\n",
        f"- model: {model}\n",
        "- API key: not recorded\n",
        "- proxy: 127.0.0.1:7897 used if available\n",
    ]

    for case_file in sorted((ROOT / "cases").glob("case-*.md")):
        case = parse_case(case_file)
        for assembly, prompt in [("A", assembly_a(case)), ("B", assembly_b(case))]:
            text, elapsed = call_llm(api_key, api_url, model, prompt)
            score, errors = score_case(case["case"], text)
            record = {
                "case": case["case"],
                "assembly": assembly,
                "model": model,
                "elapsed_seconds": elapsed,
                "prompt_retention": retention(prompt, case),
                "intermediate_auditability": "none",
                "score": score,
                "total": sum(score.values()),
                "errors": errors,
                "final_prompt": prompt,
                "text": text,
            }
            records.append(record)
            raw_lines.extend([
                f"\n## {case['case']} / Assembly {assembly}\n\n",
                f"- elapsed_seconds: {elapsed}\n",
                f"- key_info_retention: {record['prompt_retention']['ratio']}\n",
                f"- score_total: {record['total']}\n",
                f"- errors: {errors or []}\n\n",
                "### Final Prompt\n\n",
                prompt,
                "\n\n### Draft\n\n",
                text,
                "\n",
            ])
            print(case["case"], assembly, record["total"], elapsed)

        prompt_plan = plan_prompt(case)
        plan, plan_elapsed = call_llm(api_key, api_url, model, prompt_plan, max_tokens=800)
        prompt_checker = checker_prompt(case, plan)
        checker, checker_elapsed = call_llm(api_key, api_url, model, prompt_checker, max_tokens=600)
        prompt_draft = draft_prompt(case, plan, checker)
        text, draft_elapsed = call_llm(api_key, api_url, model, prompt_draft)
        score, errors = score_case(case["case"], text)
        checker_summary = parse_checker(checker)
        final_prompt = "\n\n--- C1 PLAN PROMPT ---\n\n".join(["", prompt_plan]).strip()
        final_prompt += "\n\n--- C2 CHECKER PROMPT ---\n\n" + prompt_checker
        final_prompt += "\n\n--- C3 DRAFT PROMPT ---\n\n" + prompt_draft
        record = {
            "case": case["case"],
            "assembly": "C",
            "model": model,
            "elapsed_seconds": round(plan_elapsed + checker_elapsed + draft_elapsed, 2),
            "plan_elapsed_seconds": plan_elapsed,
            "checker_elapsed_seconds": checker_elapsed,
            "draft_elapsed_seconds": draft_elapsed,
            "prompt_retention": retention(final_prompt, case),
            "intermediate_auditability": "plan_and_checker",
            "checker_summary": checker_summary,
            "score": score,
            "total": sum(score.values()),
            "errors": errors,
            "final_prompt": final_prompt,
            "plan": plan,
            "checker": checker,
            "text": text,
        }
        records.append(record)
        raw_lines.extend([
            f"\n## {case['case']} / Assembly C\n\n",
            f"- plan_elapsed_seconds: {plan_elapsed}\n",
            f"- checker_elapsed_seconds: {checker_elapsed}\n",
            f"- draft_elapsed_seconds: {draft_elapsed}\n",
            f"- key_info_retention: {record['prompt_retention']['ratio']}\n",
            f"- checker_summary: {checker_summary}\n",
            f"- score_total: {record['total']}\n",
            f"- errors: {errors or []}\n\n",
            "### Final Prompt Chain\n\n",
            final_prompt,
            "\n\n### Plan\n\n",
            plan,
            "\n\n### Checker\n\n",
            checker,
            "\n\n### Draft\n\n",
            text,
            "\n",
        ])
        print(case["case"], "C", record["total"], record["elapsed_seconds"])

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "api_base": api_url,
        "records": records,
        "aggregate": aggregate(records),
    }
    (RESULTS_DIR / "assembly-data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS_DIR / "raw-assembly-generations.md").write_text("".join(raw_lines), encoding="utf-8")
    print("DONE records", len(records))


if __name__ == "__main__":
    main()

