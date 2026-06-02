"""Lite Quality Service

集中管理 Lite 模式下的质量判断与修复逻辑。
本模块只负责质量判断和 repair messages 构建，不调用 LLM，不读写文件，不发 SSE。

Phase 3.4C 范围：
- quality_one_line: 从 review 中提取一句话质量说明
- needs_quality_repair: 判断是否需要质量修复

注意：repair prompt 使用 prompt_engine.render() 模板引擎，与业务流程耦合较深，本轮不迁移。
"""


class LiteQualityService:
    """Quality gate and repair helper for Lite mode."""

    @staticmethod
    def quality_one_line(summary: str, action: str) -> str:
        """Extract a one-line quality summary from review."""
        if summary:
            return summary.splitlines()[0][:80]
        if action == "continue":
            return "已续写草稿，并更新故事状态。"
        if action == "more_exciting":
            return "已增强冲突、爽点和结尾钩子。"
        if action == "more_reasonable":
            return "已补充人物动机和前文衔接。"
        return "已完成质量审查，并更新故事状态。"

    @staticmethod
    def needs_quality_repair(review) -> bool:
        """Determine if quality repair is needed based on review."""
        if not review:
            return False
        scores = review.scores.model_dump() if review.scores else {}
        values = [v for v in scores.values() if isinstance(v, int)]
        avg = sum(values) / len(values) if values else 10
        has_serious_issue = any(issue.severity in ("critical", "major") for issue in review.issues)
        return avg < 6 or has_serious_issue
