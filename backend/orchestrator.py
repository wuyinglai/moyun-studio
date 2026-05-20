"""
轻量多Agent编排器 — 零依赖，直接可用
用在墨韵的多步写作链（写作→审查→修订循环）

核心概念：
  Context  — 步骤间共享数据（替代 LangGraph 的 State）
  Step     — 单个Agent的抽象（接收Context，返回dict更新上下文）
  Pipeline — 串联多个步骤（线性执行）
  Branch   — 条件分支（根据上一步结果决定下一步）
"""

from collections.abc import Callable
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── 上下文：步骤间共享数据 ──────────────────────────────────

class Ctx:
    """轻量上下文，替代 LangGraph 的 State。"""
    def __init__(self, **kwargs):
        self._d = kwargs

    def get(self, key: str, default=None):
        return self._d.get(key, default)

    def set(self, key: str, value: Any):
        self._d[key] = value

    def to_dict(self):
        return self._d.copy()


# ── 步骤：单个Agent的抽象 ─────────────────────────────────────

class Step:
    """
    fn 签名：fn(ctx: Ctx) -> dict
    返回值会 merge 进上下文。
    """
    def __init__(self, name: str, fn: Callable[[Ctx], dict]):
        self.name = name
        self.fn = fn

    def run(self, ctx: Ctx) -> Ctx:
        logger.info("  ▶ %s", self.name)
        result = self.fn(ctx)
        for k, v in result.items():
            ctx.set(k, v)
        return ctx


# ── 管道：串联多个步骤 ───────────────────────────────────────

class Pipeline:
    """线性执行一系列 Step。"""
    def __init__(self, name: str, steps: list[Step]):
        self.name = name
        self.steps = steps

    def run(self, ctx: Ctx) -> Ctx:
        logger.info("▶ 管道: %s", self.name)
        for step in self.steps:
            ctx = step.run(ctx)
        logger.info("✓ %s 完成", self.name)
        return ctx


# ── 条件分支：根据上一步结果决定下一步 ─────────────────────────

class Branch:
    """
    condition: fn(ctx) -> str，返回 branches 的 key
    branches:   dict[str, Pipeline]
    """
    def __init__(self, name: str,
                 condition: Callable[[Ctx], str],
                 branches: dict[str, Pipeline]):
        self.name = name
        self.condition = condition
        self.branches = branches

    def run(self, ctx: Ctx) -> Ctx:
        logger.info("  ◆ 判断: %s", self.name)
        key = self.condition(ctx)
        logger.info("  → 进入: %s", key)
        return self.branches[key].run(ctx)


# ══════════════════════════════════════════════════════════
# 示例：墨韵写作链（写作 → 审查 → 通过/修订）
# ══════════════════════════════════════════════════════════

def _llm_call(prompt: str) -> str:
    """占位：实际调用 LiteLLM。"""
    return f"[LLM返回] {prompt[:30]}..."


def step_write(ctx: Ctx) -> dict:
    topic     = ctx.get("topic")
    outline   = ctx.get("outline", "")
    contract  = ctx.get("contract", "")
    prompt    = f"根据大纲写一章：{topic}\n大纲：{outline}\n约束：{contract}"
    draft     = _llm_call(prompt)
    return {"draft": draft, "needs_review": True}


def step_review(ctx: Ctx) -> dict:
    # 模拟返回结构化审查结果（对齐 Webnovel Writer 的 review JSON）
    review_result = {
        "passed": True,   # 实际由 LLM 判断
        "issues": [],
        "score": {"一致性": 8, "节奏": 7}
    }
    passed = review_result["passed"]
    return {
        "review_result": review_result,
        "passed_review": passed
    }


def step_revise(ctx: Ctx) -> dict:
    draft    = ctx.get("draft", "")
    issues   = ctx.get("review_result", {}).get("issues", [])
    prompt   = f"根据问题修订：{issues}\n原文：{draft[:200]}"
    revised  = _llm_call(prompt)
    return {"draft": revised}


def cond_review(ctx: Ctx) -> str:
    return "revise" if not ctx.get("passed_review") else "done"


# ── 组装墨韵写作管道 ─────────────────────────────────────────

write_pipeline = Pipeline("墨韵写作链", [
    Step("写作章节", step_write),
    Branch("审查判断", cond_review, {
        "revise": Pipeline("修订循环", [
            Step("修订章节", step_revise),
            Step("重新审查", step_review),
        ]),
        "done": Pipeline("完成", []),
    }),
])


if __name__ == "__main__":
    ctx = Ctx(
        topic="三体",
        outline="三幕结构：危机→对抗→结局",
        contract="禁止OOC；保持节奏；每章结尾留钩子"
    )
    write_pipeline.run(ctx)
    print("最终上下文：")
    for k, v in ctx.to_dict().items():
        print(f"  {k}: {str(v)[:80]}")
