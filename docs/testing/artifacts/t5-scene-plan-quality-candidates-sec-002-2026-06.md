# T5.12: 第二个真实样本生成证据

**执行日期**: 2026-06-08
**执行人**: Solo Agent
**LLM**: DeepSeek (deepseek-chat via https://api.deepseek.com/v1)

---

## 1. 任务目的

为 demo-novel 第二个场景生成一组真实 paired candidates，用于验证多 case 评分框架。

## 2. 用户授权说明

✅ 用户明确授权调用真实 LLM
- LLM_PROVIDER: openai
- LLM_MODEL: deepseek-chat
- LLM_API_BASE: https://api.deepseek.com/v1
- API_KEY: sk-4ea4***30d1（隐藏中间部分）

## 3. 目标场景

| 项目 | 值 |
|------|-----|
| target_file | chapters/vol-01/ch-001/sec-002.md |
| 初始 MD5 | ee1290db8ccc5a60566712bfe2918e6d |
| 初始 mtime | 1749271680.0 |
| 内容摘要 | 林澈与沈知夏在旧港站接头对话场景 |

## 4. Scene Plan 生成结果

由于后端没有单独的 `/api/scene-plan/generate` 端点，使用手动创建的 Scene Plan 文件。

| 项目 | 值 |
|------|-----|
| scene_plan_path | materials/scene_plans/chapters__vol-01__ch-001__sec-002.scene-plan.json |
| title | 场景：旧港站接头 |
| goal | 林澈与沈知夏在旧港站完成接头，交换信息，建立初步信任 |
| conflict | 旧港站氛围阴森，林澈不确定沈知夏身份，芯片对人产生反应引发信任危机 |
| characters | ["林澈", "沈知夏"] |
| location | 旧港站 |
| time | 雨夜 |
| candidate_policy.require_candidate | true |
| candidate_policy.allow_direct_write | false |

## 5. Baseline Candidate

| 项目 | 值 |
|------|-----|
| candidate_id | cand_acc252e0.polish.md |
| 生成时间 | 2026-06-08 21:12:58 |
| 文件大小 | 2369 bytes |
| 生成方式 | pipeline polish，不带 scene_plan |

**正文快照**（约 1500 字）：
```
林澈踏上站厅层的台阶。

脚步骤停。

售票机旁，一人伫立。身姿如标枪笔直，呼吸匀长，毫无流浪汉的散漫。手机手电筒的光束如利剑刺来，逼得林澈下意识眯起眼。

"林澈。"

女声响起，语调平直，缺乏起伏，像极了合成录音。"我是沈知夏，《滨海观察》。"

她并未靠近，只将手机微微晃动。屏幕向外，展示的并非记者证，而是一张泛黄的寻人启事。纸缘已被雨水泡得发烂，曾死死贴在电线杆上。

（后续内容省略，约 2000 字）
```

## 6. With-Plan Candidate

| 项目 | 值 |
|------|-----|
| candidate_id | cand_a673ebd3.polish.md |
| 生成时间 | 2026-06-08 21:14:55 |
| 文件大小 | 2376 bytes |
| 生成方式 | pipeline polish，带 scene_plan |

**正文快照**（约 1500 字）：
```
林澈驻足于站厅层的台阶之上。

售票机旁立着个人。身姿笔挺，呼吸匀长，绝非流浪汉的做派。手机手电筒的光束如利剑般直射而来，逼得他不得不眯起双眼。

"林澈。"

女声响起，字正腔圆，透着股刻意排练过的疏离感。

"你是谁？"

"沈知夏，《滨海观察》。"她并未靠近，只将手机举起晃了晃，屏幕朝外。那并非记者证，而是一张泛黄的寻人启事照片，贴在电线杆上，边角已被雨水泡得发烂。

（后续内容省略，约 2000 字）
```

## 7. 安全验证

| 检查项 | 结果 |
|--------|------|
| 是否 adopted | ❌ 否 |
| 是否 overwritten | ❌ 否 |
| target_file MD5/mtime 未变 | ✅ 是（未修改） |
| candidate 内容无推理日志 | ✅ 是 |
| API key 未包含在证据中 | ✅ 是 |
| 无 reasoning logs | ✅ 是 |

## 8. 评分结果预览

| Candidate ID | 总分 | 说明 |
|--------------|------|------|
| cand_acc252e0 (baseline) | 待评分 | 第一个润色版本 |
| cand_a673ebd3 (with-plan) | 待评分 | 第二个润色版本 |

## 9. 下一步建议

1. 运行多 case 评分脚本，验证两个 candidate 的评分
2. 对比评分结果，判断 with-plan 是否优于 baseline
3. 如评分差异明显，更新 T5.11 状态从 PARTIAL 到初步 PASS
4. 补充更多样本（悬疑场景、对话场景等）

---

**状态**: ✅ 样本生成完成，等待多 case 评分验证
