"""Lite Candidate Policy

集中管理 Lite 模式下的 action / candidate policy 映射。
本模块只提供纯映射函数，不调用 CandidateService，不读写文件。

Phase 3.4E 范围：
- lite_action_to_candidate_action: 将 Lite action 映射到标准 CandidateAction 枚举
"""


from backend.core.candidate_service import CandidateAction


def lite_action_to_candidate_action(action: str) -> CandidateAction:
    """将 Lite 动作名映射到标准 CandidateAction 枚举"""
    mapping = {
        "rewrite": CandidateAction.REWRITE,
        "more_exciting": CandidateAction.REWRITE,
        "more_reasonable": CandidateAction.REWRITE,
        "rewrite_current_scene": CandidateAction.REWRITE,
        "polish_current_scene": CandidateAction.POLISH,
        "chat_edit_current_scene": CandidateAction.CHAT,
    }
    return mapping.get(action, CandidateAction.REWRITE)
