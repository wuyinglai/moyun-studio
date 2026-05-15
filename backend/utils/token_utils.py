"""Token 估算工具函数

提供统一的 token 估算回退逻辑，避免在三处重复。
"""

import re


def estimate_tokens_fallback(text: str) -> int:
    """估算文本 token 数（回退方法，不依赖 tiktoken）

    中文字符 ≈ 0.5 token，其他字符 ≈ 0.25 token
    """
    chinese = len(re.findall(r'[一-鿿]', text))
    other = len(text) - chinese
    return int(chinese * 0.5 + other * 0.25)
