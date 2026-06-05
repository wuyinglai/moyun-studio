# Review Engine 真实 LLM Review 小冒烟报告

- **Phase**: T3-D7.3c
- **Status**: ✅ SUCCESS
- **Mode**: llm_review
- **LLM Called**: Yes
- **Note**: REAL-RUN: LLM 调用成功

## 统计

- Total Candidates: 14

## 输出 JSON

```json
{
  "phase": "T3-D7.1.1",
  "engine": "review_engine",
  "mode": "llm_review",
  "llm_called": true,
  "auto_write_settings": false,
  "reviews": [
    {
      "candidate_id": "scene-line003-new_item-着昏黄的灯",
      "confirmed": false,
      "confidence": 0.1,
      "severity": "P3",
      "action": "suggest_ignore",
      "needs_user_confirmation": false,
      "reason": "提取噪声，'着昏黄的灯'是描述性短语而非道具名称"
    },
    {
      "candidate_id": "scene-line005-new_faction-李玄推阁",
      "confirmed": false,
      "confidence": 0.1,
      "severity": "P3",
      "action": "suggest_ignore",
      "needs_user_confirmation": false,
      "reason": "提取噪声，'李玄推阁'是动作描述（李玄推开阁门），非势力名称"
    },
    {
      "candidate_id": "scene-line007-new_character-沈鹤年",
      "confirmed": true,
      "confidence": 0.95,
      "severity": "P1",
      "action": "suggest_add_to_settings",
      "needs_user_confirmation": true,
      "reason": "正文出现角色名，设定库无记录，符合新角色特征",
      "suggested_target": "settings/characters.md",
      "suggested_entry": {
        "name": "沈鹤年",
        "type": "character",
        "role": "墨香阁掌柜"
      }
    },
    {
      "candidate_id": "scene-line009-new_item-玄黄秘录",
      "confirmed": true,
      "confidence": 0.9,
      "severity": "P2",
      "action": "suggest_add_to_settings",
      "needs_user_confirmation": true,
      "reason": "正文出现疑似道具/书籍，但道具设定库未记录",
      "suggested_target": "settings/items.md",
      "suggested_entry": {
        "name": "玄黄秘录",
        "type": "item",
        "role": "古籍"
      }
    },
    {
      "candidate_id": "scene-line009-new_term-叫《玄黄秘录",
      "confirmed": false,
      "confidence": 0.1,
      "severity": "P3",
      "action": "suggest_ignore",
      "needs_user_confirmation": false,
      "reason": "提取噪声，'叫《玄黄秘录'是语法片段，非术语"
    },
    {
      "candidate_id": "scene-line011-new_item-一枚玄铁令牌",
      "confirmed": true,
      "confidence": 0.85,
      "severity": "P2",
      "action": "suggest_add_to_settings",
      "needs_user_confirmation": true,
      "reason": "正文出现疑似道具，但道具设定库未记录",
      "suggested_target": "settings/items.md",
      "suggested_entry": {
        "name": "玄铁令牌",
        "type": "item",
        "role": "身份信物"
      }
    },
    {
      "candidate_id": "scene-line011-new_item-着一枚玄铁",
      "confirmed": false,
      "confidence": 0.1,
      "severity": "P3",
      "action": "suggest_ignore",
      "needs_user_confirmation": false,
      "reason": "提取噪声，'着一枚玄铁'是描述性短语，非道具名称"
    },
    {
      "candidate_id": "scene-line015-new_item-一盏青铜灯",
      "confirmed": true,
      "confidence": 0.8,
      "severity": "P2",
      "action": "suggest_add_to_settings",
      "needs_user_confirmation": true,
      "reason": "正文出现疑似道具，但道具设定库未记录",
      "suggested_target": "settings/items.md",
      "suggested_entry": {
        "name": "青铜灯",
        "type": "item",
        "role": "室内陈设"
      }
    },
    {
      "candidate_id": "scene-line015-new_item-淡的龙涎香",
      "confirmed": false,
      "confidence": 0.1,
      "severity": "P3",
      "action": "suggest_ignore",
      "needs_user_confirmation": false,
      "reason": "提取噪声，'淡的龙涎香'是描述性短语，非道具名称"
    },
    {
      "candidate_id": "scene-line021-new_faction-知道天机阁",
      "confirmed": false,
      "confidence": 0.1,
      "severity": "P3",
      "action": "suggest_ignore",
      "needs_user_confirmation": false,
      "reason": "提取噪声，'知道天机阁'是动作描述，非势力名称"
    },
    {
      "candidate_id": "scene-line025-new_term-五曜珠",
      "confirmed": true,
      "confidence": 0.9,
      "severity": "P2",
      "action": "suggest_add_to_settings",
      "needs_user_confirmation": true,
      "reason": "正文出现疑似术语/特殊物品，但术语设定库未记录",
      "suggested_target": "settings/terms.md",
      "suggested_entry": {
        "name": "五曜珠",
        "type": "term",
        "role": "开启玄黄秘境的钥匙"
      }
    },
    {
      "candidate_id": "scene-line025-new_term-开启玄黄秘境",
      "confirmed": true,
      "confidence": 0.85,
      "severity": "P2",
      "action": "suggest_add_to_settings",
      "needs_user_confirmation": true,
      "reason": "正文出现疑似术语/特殊物品，但术语设定库未记录",
      "suggested_target": "settings/terms.md",
      "suggested_entry": {
        "name": "开启玄黄秘境",
        "type": "term",
        "role": "事件/目标"
      }
    },
    {
      "candidate_id": "scene-line025-new_term-黄秘境的钥匙",
      "confirmed": false,
      "confidence": 0.1,
      "severity": "P3",
      "action": "suggest_ignore",
      "needs_user_confirmation": false,
      "reason": "提取噪声，'黄秘境的钥匙'是描述性短语，非术语"
    },
    {
      "candidate_id": "scene-line027-new_faction-墨香阁的阁",
      "confirmed": false,
      "confidence": 0.1,
      "severity": "P3",
      "action": "suggest_ignore",
      "needs_user_confirmation": false,
      "reason": "提取噪声，'墨香阁的阁'是语法片段，非势力名称"
    }
  ]
}
```