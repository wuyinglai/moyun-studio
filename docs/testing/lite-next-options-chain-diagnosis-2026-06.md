# Lite next-options 链路诊断报告

## 1. 背景

根据 Phase T3-B-10 的测试结果：
- 第 1 场 Agnes LLM 真实生成成功，1095 字符；
- "生成下一场景爽点卡"按钮已经出现；
- 测试脚本可以找到并点击该按钮；
- 但点击后没有出现 `lite-option-card`；
- 第 2、3 场因此没有执行。

本报告旨在定位问题发生在 next-options 链路的具体环节。

## 2. 期望链路

```
按钮点击 → refreshOptions → fetchLiteNextOptions → 后端 next-options API → 返回 cards → nextCards 更新 → lite-option-card 渲染
```

## 3. 实际链路观察

根据代码分析，期望链路的每个环节理论上应该正常工作。但实际测试中点击按钮后没有出现卡片，说明链路中某一层存在问题。

## 4. 前端代码链路

### 4.1 文件清单

| 文件 | 路径 | 作用 |
|------|------|------|
| LiteWritingView.vue | `frontend/src/views/LiteWritingView.vue` | 按钮定义和卡片渲染 |
| useLiteGeneration.ts | `frontend/src/composables/useLiteGeneration.ts` | refreshOptions 函数实现 |
| liteService.ts | `frontend/src/services/liteService.ts` | API 请求封装 |

### 4.2 按钮点击处理

按钮定义在 `LiteWritingView.vue` 第 265-272 行：

```vue
<button
  v-if="!nextCards.length && !loadingOptions && !generating"
  class="primary-btn full"
  data-testid="lite-generate-next-options"
  @click="refreshOptions"
>
  生成下一场景爽点卡
</button>
```

点击直接调用 `refreshOptions` 函数。

### 4.3 refreshOptions 函数

定义在 `useLiteGeneration.ts` 第 416-444 行：

```typescript
async function refreshOptions(baseFile = deps.currentFilePath.value || null, overridePrefs?: LiteWritingPrefs) {
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  const requestId = ++optionRequestId.value
  loadingOptions.value = true
  optionError.value = ''
  nextCards.value = []
  setWorkStatus('正在生成爽点卡', '正在读取前文、故事引擎和近期上下文，给下一场景准备 3 个方向。')
  try {
    const data = await fetchLiteNextOptions(projectId, baseFile, overridePrefs || deps.prefs)
    if (requestId !== optionRequestId.value) return
    setWorkStatus('爽点卡已生成', '下一场景方向已经准备好，可以选择一张卡继续写。')
    nextCards.value = data.cards
    nextTargetFile.value = data.next_file
    if (!data.cards.length) {
      optionError.value = '这次没有生成出爽点卡，点"刷新"再试一次。'
      nextTargetFile.value = ''
    }
  } catch {
    if (requestId !== optionRequestId.value) return
    optionError.value = '爽点卡生成失败，点"刷新"重试。'
    nextTargetFile.value = ''
  } finally {
    if (requestId === optionRequestId.value) {
      loadingOptions.value = false
      clearWorkStatus()
    }
  }
}
```

### 4.4 fetchLiteNextOptions API 调用

定义在 `liteService.ts` 第 75-81 行：

```typescript
export async function fetchLiteNextOptions(projectId: string, currentFile: string | null, prefs: LiteWritingPrefs) {
  return await api.post<LiteNextOptionsResponse>(API_ROUTES.liteNextOptions, {
    project_id: projectId,
    current_file: currentFile,
    prefs,
  })
}
```

API 路径为 `/lite/next-options`。

### 4.5 响应处理

响应接口定义：

```typescript
export interface LiteNextOptionsResponse {
  cards: LiteNextOptionCard[]
  current_file: string
  next_file: string
}
```

## 5. 后端 API 链路

### 5.1 API 定义

路径：`POST /lite/next-options`

请求体：
- `project_id`: string (必需)
- `current_file`: string | null
- `prefs`: LiteWritingPrefs

响应：
```json
{
  "status": "success",
  "data": {
    "cards": [...],
    "current_file": "...",
    "next_file": "..."
  },
  "message": "..."
}
```

### 5.2 核心处理逻辑

后端处理流程：

1. 验证项目 ID 和文件路径
2. 读取当前内容、故事引擎、近期上下文
3. 生成 fallback 兜底卡片
4. 尝试调用 LLM 生成动态卡片
5. 如果 LLM 返回 3 张卡片，则使用动态卡片；否则使用 fallback

关键代码在 `backend/api/lite.py` 第 487-545 行：

```python
cards = LiteOptionCardsService.fallback_next_cards(next_label, context_content, recent_context)
try:
    # LLM 调用生成动态卡片
    parsed_cards = LiteOptionCardsService.parse_option_cards(raw, next_label)
    if len(parsed_cards) == 3:
        cards = parsed_cards
except Exception as e:
    logger.warning("动态生成爽点卡失败，使用上下文兜底卡: %s", e)
return ApiResponse.ok(LiteNextOptionsResponse(
    cards=cards,
    current_file=req.current_file or chapter_path(current_no),
    next_file=next_file,
))
```

**重要发现**：后端始终返回 `cards` 数组，即使 LLM 调用失败也会返回 fallback 卡片。

## 6. Network 诊断结果

由于无法实际运行测试环境，建议通过诊断脚本 `tests/phase-t3b-next-options-diagnosis.py` 运行后获取以下信息：

- 是否发出 `/lite/next-options` 请求
- 请求状态码
- 返回的 cards 数量
- 请求体参数

## 7. Console / Error 观察

需要检查：

1. 是否有 JavaScript 控制台错误
2. `optionError` 是否被设置
3. `loadingOptions` 是否正确显示和隐藏

## 8. 根因判断

根据代码分析和测试现象，可能的根因：

**当前判断：D. API 成功但 cards 为空**

**理由**：

1. 后端代码显示有 fallback 机制，理论上不会返回空数组
2. 但 `LiteOptionCardsService.fallback_next_cards` 的实现可能存在问题
3. 或者 LLM 返回的卡片解析失败后回退到空数组

**其他可能性**：

- **C. next-options API 请求失败**：网络问题或后端错误
- **E. API 成功返回 cards，但前端没有渲染**：Vue 响应式更新问题

## 9. 最小修复建议

### 9.1 前端增强

在 `refreshOptions` 函数中增加日志输出：

```typescript
async function refreshOptions(...) {
  // ...
  try {
    const data = await fetchLiteNextOptions(projectId, baseFile, overridePrefs || deps.prefs)
    console.log('next-options response:', data)
    // ...
  } catch (e) {
    console.error('next-options error:', e)
    // ...
  }
}
```

### 9.2 后端增强

在 `generate_next_options` 函数中确保 fallback 卡片始终不为空：

```python
cards = LiteOptionCardsService.fallback_next_cards(next_label, context_content, recent_context)
if not cards:
    # 确保至少有一张兜底卡片
    cards = [create_default_card(next_label)]
```

### 9.3 调试步骤

1. 运行诊断脚本观察网络请求
2. 检查浏览器控制台错误
3. 查看后端日志

## 10. 是否可以进入修复任务

**建议进入 Phase T3-B-12**

当前已完成链路分析，定位到可能的问题区域。建议：

1. 首先运行诊断脚本获取实际网络和响应数据
2. 根据诊断结果进行针对性修复
3. 修复后重新运行连续生成测试

## 11. 实测诊断结果

### 运行时间
2026-06-03 17:26:14

### 诊断脚本
`tests/phase-t3b-next-options-diagnosis.py`

### Network 结果
| 项目 | 结果 |
|------|------|
| 是否看到 /lite/next-options 请求 | 是 |
| method | POST |
| status | 200 |
| cards 数量 | 3 |

### UI 结果
| 项目 | 结果 |
|------|------|
| 是否点击 lite-generate-next-options | 是 |
| 是否出现 lite-option-card | 否 |
| optionError | 空 |
| console errors | 空 |

### 返回的卡片样本
| ID | 标题 |
|----|------|
| next-第1卷 第1章 第2场景-1 | 当场反逼 |
| next-第1卷 第1章 第2场景-2 | 旧账翻面 |
| next-第1卷 第1章 第2场景-3 | 战果藏钩 |

### 根因结论

**E. API 成功返回 cards，但前端没有渲染**

### 证据文件
`docs/testing/screenshots/t3b-next-options-diagnosis.json`

### 是否进入 T3-B-12

**是**

原因：已明确定位问题。API 成功返回 3 张卡片，但前端没有渲染。需要检查前端响应式更新或渲染逻辑问题。