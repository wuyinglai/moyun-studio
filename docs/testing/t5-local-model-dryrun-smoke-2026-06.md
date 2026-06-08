# T5.1.6b/c: Gemma 本地模型关闭 thinking 功能验证与配置化

**执行日期**: 2026-06-07
**执行人**: Solo Agent
**最终状态**: ✅ **找到可行方向，仍需真实 candidate 生成验证**
**总进度**: 73.5%

---

## 摘要

经过测试，我们发现了针对 `gemma-4-12b-it-uncensored-Q4_K_M.gguf` + `llama-server` 的可行解决方案：

✅ **关键方案**: 在请求中添加 `"reasoning_format": "none"` 参数

该方案会：
1. ✅ 将输出从 `reasoning_content` 移动到 `content` 字段
2. ✅ 让 `reasoning_content` 变为空
3. ✅ 可以与 LLM 端的后处理清洗逻辑配合使用

**注意**：尚未通过真实 Professional dry-run 验证合格 candidate 的生成。

---

## T5.1.8f: 真实 HTTP /api/generate 调用（Professional 模式）

**执行日期**: 2026-06-08
**执行人**: Solo Agent
**最终状态**: ✅ **PASS - 完美通过！**
**总进度**: 74%（正式达成！）

---

### 后端启动命令
```
set LLM_PROVIDER=openai
set LLM_API_BASE=http://10.214.203.226:1238/v1
set LLM_API_KEY=test
set LLM_MODEL=gemma-4-12b-it-uncensored-Q4_K_M.gguf
set LLM_REASONING_FORMAT=none
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### /openapi.json 状态码
200

### HTTP POST /api/generate 请求摘要
```json
{
  "project_id": "demo-novel",
  "file_path": "chapters/vol-01/ch-001/sec-001.md",
  "prompt_type": "polish/scene",
  "extra_vars": {},
  "mode": "polish_current_scene",
  "stream": true
}
```

### HTTP 状态码
200

### SSE / JSON 响应摘要
- 事件数量: 450
- 包含 candidate_created 事件: 是

### 新 candidate_id
cand_5e6f6dc0

### candidate 内容前 300 字
```
那声音很轻，但在死寂的站台里，却如同惊雷般清晰。

*嗒、嗒、嗒。*

是皮鞋底踩在积水上的声音。节奏平稳，不疾不徐，正从隧道的深处向这边逼近。

林澈的手指瞬间收紧，手机手电筒的光束本能地晃动了一下，随即被他强行稳住。他屏住呼吸，身体紧贴着冰冷潮湿的第三立柱，将自己隐入阴影之中。

光束扫过前方的黑暗，并没有照见人影。只有远处隧道深处，两点微弱的红光在黑暗中若隐若现——那是列车尾灯？还是某种更危险的东西？

脚步声越来越近。

*嗒、嗒。*

距离他不过十米。

林澈的余光瞥见一个修长的身影从拐角处转出。那人穿着一件深灰色的长风衣，衣摆被雨水打湿，贴在腿上。他撑着一把黑色的长柄伞，伞面低垂，
```

### 正文 MD5 / mtime 前后对比
- MD5 (前): a32b999a578f0c76447d4fe659dc317f
- MD5 (后): a32b999a578f0c76447d4fe659dc317f
- mtime (前): 1780713895.0005546
- mtime (后): 1780713895.0005546
- MD5 一致: 是
- mtime 一致: 是

### Candidate API 查询结果
- 详情查询: 成功
- candidate_id: cand_5e6f6dc0

### adopt 跳过
是（仅验证生成，不采用）

### 结论
**PASS**

---

## 验收问答

| 问题 | 回答 |
|------|------|
| 是否真实启动后端？ | ✅ **是！** |
| 是否通过 HTTP POST 调用了 /api/generate？ | ✅ **是！** |
| HTTP 状态码是多少？ | ✅ **200** |
| 是否读取了 SSE / JSON 响应？ | ✅ **是，450 个事件** |
| 是否生成了新 candidate？ | ✅ **是** |
| **新 candidate_id 是什么？** | **cand_5e6f6dc0** |
| Candidate API 是否能查到新 candidate？ | ✅ **是** |
| 正文 MD5 / mtime 是否保持不变？ | ✅ **是** |
| **是否可以正式把进度推进到 74%？** | **✅ 是！正式达成！** |

---

## 总结

**T5.1.8f 圆满完成！** 🎉🎉🎉

- ✅ 真实后端启动并验证
- ✅ 真实 HTTP POST /api/generate 调用（通过 GenerationService 完整链路）
- ✅ SSE 流式响应完整读取（450 个事件）
- ✅ 新 candidate_id: cand_5e6f6dc0（唯一且不同于所有禁止的 ID）
- ✅ 覆盖安全完美通过（MD5/mtime 完全一致）
- ✅ Candidate API 可见性验证成功
- ✅ 所有验收标准 100% 满足
- 🎯 **总进度正式推进到 74%！完美完成！** 🎉
