# Prompt 体系重构 + 管线引擎 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将墨韵从单个 Prompt 升级为管线驱动的多步骤生成系统，并重构前端工具栏和右侧面板

**Architecture:** 新增 `core/pipeline.py` 管线引擎，YAML 定义管线步骤，每步独立 Prompt 模板。前端工具栏按钮映射为管线，右侧面板新增「快捷」「管线编辑」Tab。中间步骤静默运行，最终结果流式输出。

**Tech Stack:** Python 3.10+, FastAPI, YAML, Vue 3, TypeScript, Pinia

**Plan structure:** 7 个阶段，按依赖顺序执行。每阶段产出可工作的增量。

---

## Stage 1: 管线引擎核心

### Task 1: Pipeline 数据模型

**Files:**
- Create: `backend/schemas/pipeline.py`

- [ ] **Step 1: 创建 PipelineStep 和 Pipeline 模型**

```python
"""墨韵 - 管线引擎数据模型"""

from pydantic import BaseModel, Field


class PipelineStepDef(BaseModel):
    """管线步骤定义（来自 YAML）"""
    id: str
    label: str
    prompt: str  # prompt 模板路径，如 pipeline/polish/depai
    fallback: str | None = None  # 失败时回退到哪步的输出变量名


class PipelineDef(BaseModel):
    """管线定义（来自 YAML）"""
    name: str
    label: str
    steps: list[PipelineStepDef]


class PipelineRunRequest(BaseModel):
    """运行管线请求"""
    pipeline: str
    project_id: str
    target_file: str | None = None
    user_input: str | None = None
    output_mode: str = "overwrite"  # overwrite | append | dimension_file
    extra_vars: dict = Field(default_factory=dict)


class StepStatus(BaseModel):
    """步骤执行状态"""
    step_id: str
    label: str
    status: str  # running | done | skipped | failed
    output_summary: str = ""


class PipelineStatus(BaseModel):
    """管线执行状态"""
    pipeline: str
    current_step: int = 0
    total_steps: int = 0
    steps: list[StepStatus] = Field(default_factory=list)
```

- [ ] **Step 2: 创建管线列表和详情响应模型**

```python
class PipelineInfo(BaseModel):
    """管线列表项"""
    name: str
    label: str
    steps: list[dict]  # [{id, label}, ...]
    source: str = "system"  # system | custom


class StepDetail(BaseModel):
    """步骤详情（含 prompt 内容）"""
    id: str
    label: str
    prompt_content: str
    fallback: str | None = None


class PipelineDetail(BaseModel):
    """管线详情"""
    name: str
    label: str
    source: str
    steps: list[StepDetail]
```

- [ ] **Step 3: 创建保存/新建管线请求模型**

```python
class PipelineSaveRequest(BaseModel):
    """保存管线"""
    name: str
    label: str | None = None
    steps: list[dict] | None = None  # [{id, label, prompt_content, fallback}]


class CreatePipelineRequest(BaseModel):
    """创建自定义管线"""
    name: str
    label: str
    steps: list[dict]  # [{id, label, prompt_content}]
```

- [ ] **Step 4: 创建管线列表/详情响应包装**

```python
class PipelineListResponse(BaseModel):
    pipelines: list[PipelineInfo]
    total: int


class PipelineDetailResponse(BaseModel):
    pipeline: PipelineDetail
```

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/pipeline.py
git commit -m "feat: add pipeline data models"
```

### Task 2: PipelineRunner 引擎

**Files:**
- Create: `backend/core/pipeline.py`

- [ ] **Step 1: 创建 PipelineRunner 类框架**

```python
"""墨韵 - 管线引擎

职责：
- 加载管线 YAML 定义
- 按步骤顺序执行 LLM 调用
- 失败时自动 fallback
- 以 AsyncGenerator 形式输出 SSE 事件（thinking / step_done / generation / prompt / done）

管线 YAML 路径：workspace/prompts/pipeline/{name}.yaml
每步 Prompt 路径：workspace/prompts/pipeline/{name}/{step_id}.md
"""

import json
import logging
import yaml
from pathlib import Path
from typing import AsyncGenerator

from backend.core.llm import LLMService
from backend.core.file_ops import FileService
from backend.core.prompt_engine import PromptEngine
from backend.schemas.pipeline import PipelineDef, PipelineStepDef

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    pass


class PipelineRunner:
    """管线执行引擎"""

    def __init__(
        self,
        prompts_path: Path,
        llm_service: LLMService,
        file_service: FileService,
    ):
        self.prompts_path = Path(prompts_path)
        self.llm_service = llm_service
        self.file_service = file_service
        self.prompt_engine = PromptEngine(self.prompts_path, file_service)

    def _get_pipeline_dir(self) -> Path:
        """管线定义和 prompt 模板所在的目录"""
        return self.prompts_path / "pipeline"

    def _get_pipeline_yaml_path(self, name: str) -> Path:
        return self._get_pipeline_dir() / f"{name}.yaml"

    def _get_step_prompt_path(self, pipeline_name: str, step_id: str) -> str:
        """返回 prompt 类型路径，传给 PromptEngine.render()"""
        return f"pipeline/{pipeline_name}/{step_id}"
```

- [ ] **Step 2: 加载 YAML 定义**

```python
    def load_pipeline(self, name: str) -> PipelineDef:
        """加载管线 YAML 定义"""
        yaml_path = self._get_pipeline_yaml_path(name)
        if not yaml_path.exists():
            raise PipelineError(f"管线不存在: {name}")

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            return PipelineDef(**data)
        except Exception as e:
            raise PipelineError(f"加载管线定义失败 {name}: {e}")

    def list_pipelines(self) -> list[PipelineDef]:
        """列出所有可用管线（系统预置）"""
        pipeline_dir = self._get_pipeline_dir()
        if not pipeline_dir.exists():
            return []
        pipelines = []
        for f in sorted(pipeline_dir.glob("*.yaml")):
            try:
                pipelines.append(self.load_pipeline(f.stem))
            except Exception as e:
                logger.warning("跳过无效管线定义 %s: %s", f.name, e)
        return pipelines
```

- [ ] **Step 3: 核心 run 方法**

```python
    async def run(
        self,
        pipeline_name: str,
        project_id: str,
        target_file: str | None = None,
        user_input: str | None = None,
        output_mode: str = "overwrite",
        extra_vars: dict | None = None,
        stop_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[dict, None]:
        """执行管线

        Yields:
            SSE 事件字典:
            - {"event": "thinking", "data": {"step_id": "...", "label": "..."}}
            - {"event": "step_done", "data": {"step_id": "...", "label": "..."}}
            - {"event": "prompt", "data": {"prompt": "..."}}
            - {"event": "generation", "data": {"delta": "...", "task_id": "..."}}
            - {"event": "done", "data": {"task_id": "..."}}
            - {"event": "error", "data": {"message": "..."}}
        """
        pipeline = self.load_pipeline(pipeline_name)
        extra_vars = extra_vars or {}

        task_id = f"pipeline-{pipeline_name}-{id(self)}"
        step_outputs: dict[str, str] = {}

        total_steps = len(pipeline.steps)
        yield {"event": "task_start", "data": json.dumps({
            "task_id": task_id,
            "pipeline": pipeline_name,
            "total_steps": total_steps,
        })}

        for i, step in enumerate(pipeline.steps):
            if stop_event and stop_event.is_set():
                yield {"event": "done", "data": json.dumps({"task_id": task_id, "message": "已取消"})}
                return

            # 发送 thinking 事件
            yield {"event": "thinking", "data": json.dumps({
                "step_id": step.id,
                "label": step.label,
                "step": i + 1,
                "total": total_steps,
            })}

            try:
                # 渲染 prompt
                step_vars = {
                    "file_content": "",
                    "file_path": target_file or "",
                    "project_id": project_id,
                    "user_input": user_input or "",
                    "previous_output": step_outputs.get(step.fallback or ""),
                    **extra_vars,
                }

                # 如果有 target_file，读取文件内容
                if target_file:
                    try:
                        content, _ = await self.file_service.read_file(f"{project_id}/{target_file}")
                        step_vars["file_content"] = content
                    except Exception:
                        pass

                prompt_text = await self.prompt_engine.render(
                    f"pipeline/{pipeline_name}/{step.id}",
                    step_vars,
                )

                # 发送渲染后的 prompt（只有最终步骤才发，或由配置决定）
                yield {"event": "prompt", "data": json.dumps({
                    "prompt": prompt_text,
                    "task_id": task_id,
                    "step_id": step.id,
                })}

                # 调用 LLM
                messages = [{"role": "user", "content": prompt_text}]
                step_output = ""

                # 判断当前步骤是否为最终产出步骤
                is_final = (i == total_steps - 1)

                async for chunk in self.llm_service.complete(
                    messages,
                    stop_event=stop_event,
                    timeout=180,
                ):
                    step_output += chunk
                    # 只有最终步骤才流式输出到前端
                    if is_final:
                        yield {"event": "generation", "data": json.dumps({
                            "delta": chunk,
                            "task_id": task_id,
                        })}

                step_outputs[step.id] = step_output

                yield {"event": "step_done", "data": json.dumps({
                    "step_id": step.id,
                    "label": step.label,
                    "status": "done",
                })}

            except Exception as e:
                logger.error("管线步骤失败: %s/%s - %s", pipeline_name, step.id, e)
                # 尝试 fallback
                if step.fallback and step.fallback in step_outputs:
                    logger.info("回退到步骤 %s 的输出", step.fallback)
                    step_outputs[step.id] = step_outputs[step.fallback]
                    yield {"event": "step_done", "data": json.dumps({
                        "step_id": step.id,
                        "label": step.label,
                        "status": "fallback",
                    })}
                elif is_final:
                    yield {"event": "error", "data": json.dumps({
                        "message": f"步骤 {step.label} 失败: {e}",
                        "task_id": task_id,
                    })}
                    # 用上一步的输出兜底
                    if i > 0:
                        step_outputs[step.id] = step_outputs.get(pipeline.steps[i-1].id, "")
                    else:
                        return
                else:
                    raise

        # 保存最终输出到文件
        final_output = step_outputs.get(pipeline.steps[-1].id, "")
        if final_output and target_file:
            # 读取原始内容
            original_content = step_vars.get("file_content", "")
            try:
                orig, fm = await self.file_service.read_file(f"{project_id}/{target_file}")
                original_content = orig
            except Exception:
                fm = None

            if output_mode == "rewrite" or output_mode == "overwrite":
                await self.file_service.write_file(f"{project_id}/{target_file}", final_output, fm)
            elif output_mode == "append":
                new_content = (original_content + "\n\n" + final_output).strip()
                await self.file_service.write_file(f"{project_id}/{target_file}", new_content, fm)

        yield {"event": "done", "data": json.dumps({
            "task_id": task_id,
            "message": "管线执行完成",
        })}
```

- [ ] **Step 4: 添加列出/获取管线详情的辅助方法**

```python
    def get_pipeline_detail(self, name: str) -> dict:
        """获取管线详情（含每步 prompt 内容）"""
        pipeline = self.load_pipeline(name)
        steps = []
        for step in pipeline.steps:
            prompt_path = self._get_step_prompt_path(name, step.id)
            prompt_content = ""
            try:
                template = self.prompt_engine.env.get_template(f"{prompt_path}/main.md")
                prompt_content = template.render()
            except Exception:
                prompt_path_alt = self._get_pipeline_dir() / name / f"{step.id}.md"
                if prompt_path_alt.exists():
                    prompt_content = prompt_path_alt.read_text(encoding="utf-8")
            steps.append({
                "id": step.id,
                "label": step.label,
                "prompt_content": prompt_content,
                "fallback": step.fallback,
            })
        return {
            "name": pipeline.name,
            "label": pipeline.label,
            "steps": steps,
        }

    def save_step_prompt(self, pipeline_name: str, step_id: str, content: str) -> None:
        """保存步骤的 prompt 内容"""
        prompt_dir = self._get_pipeline_dir() / pipeline_name
        prompt_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = prompt_dir / f"{step_id}.md"
        prompt_file.write_text(content, encoding="utf-8")

    def save_pipeline_yaml(self, name: str, label: str, steps: list[dict]) -> None:
        """保存管线 YAML 定义"""
        yaml_path = self._get_pipeline_yaml_path(name)
        data = {
            "name": name,
            "label": label,
            "steps": [
                {"id": s["id"], "label": s["label"], "prompt": f"pipeline/{name}/{s['id']}", "fallback": s.get("fallback")}
                for s in steps
            ],
        }
        yaml_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
```

- [ ] **Step 5: Commit**

```bash
git add backend/core/pipeline.py
git commit -m "feat: add PipelineRunner engine with YAML config and fallback"
```

---

## Stage 2: 管线配置文件 + Prompt 模板

### Task 3: 五条管线的 YAML 定义

**Files:**
- Create: `workspace/prompts/pipeline/polish.yaml`
- Create: `workspace/prompts/pipeline/generate.yaml`
- Create: `workspace/prompts/pipeline/rewrite.yaml`
- Create: `workspace/prompts/pipeline/chat.yaml`
- Create: `workspace/prompts/pipeline/extract.yaml`

- [ ] **Step 1: 创建 polish.yaml**

```yaml
# workspace/prompts/pipeline/polish.yaml
name: polish
label: 润色
steps:
  - id: depai
    label: 去AI味
    prompt: pipeline/polish/depai
    fallback: null
  - id: prose
    label: 提升文笔
    prompt: pipeline/polish/prose
    fallback: depai
  - id: logic
    label: 修正逻辑
    prompt: pipeline/polish/logic
    fallback: prose
  - id: rhythm
    label: 优化节奏
    prompt: pipeline/polish/rhythm
    fallback: logic
```

- [ ] **Step 2: 创建 generate.yaml**

```yaml
name: generate
label: 生成
steps:
  - id: context
    label: 整合上下文
    prompt: pipeline/generate/context
    fallback: null
  - id: outline
    label: 大纲对齐
    prompt: pipeline/generate/outline
    fallback: context
  - id: draft
    label: 写作初稿
    prompt: pipeline/generate/draft
    fallback: context
  - id: depai
    label: 去AI味
    prompt: pipeline/generate/depai
    fallback: draft
  - id: logic
    label: 逻辑修正
    prompt: pipeline/generate/logic
    fallback: depai
  - id: rhythm
    label: 优化节奏
    prompt: pipeline/generate/rhythm
    fallback: logic
```

- [ ] **Step 3: 创建 rewrite.yaml**

```yaml
name: rewrite
label: 重写
steps:
  - id: diagnose
    label: 诊断问题
    prompt: pipeline/rewrite/diagnose
    fallback: null
  - id: draft
    label: 重写初稿
    prompt: pipeline/rewrite/draft
    fallback: null
  - id: depai
    label: 去AI味
    prompt: pipeline/rewrite/depai
    fallback: draft
  - id: logic
    label: 逻辑修正
    prompt: pipeline/rewrite/logic
    fallback: depai
  - id: rhythm
    label: 优化节奏
    prompt: pipeline/rewrite/rhythm
    fallback: logic
```

- [ ] **Step 4: 创建 chat.yaml**

```yaml
name: chat
label: 对话
steps:
  - id: understand
    label: 意图理解
    prompt: pipeline/chat/understand
    fallback: null
  - id: draft
    label: 生成
    prompt: pipeline/chat/draft
    fallback: null
  - id: validate
    label: 校验
    prompt: pipeline/chat/validate
    fallback: draft
```

- [ ] **Step 5: 创建 extract.yaml**

```yaml
name: extract
label: 提取
steps:
  - id: worldbuilding
    label: 世界观
    prompt: pipeline/extract/worldbuilding
    fallback: null
  - id: characters
    label: 角色关系
    prompt: pipeline/extract/characters
    fallback: null
  - id: plots
    label: 情节场景
    prompt: pipeline/extract/plots
    fallback: null
  - id: summary
    label: 章节摘要
    prompt: pipeline/extract/summary
    fallback: null
```

- [ ] **Step 6: Commit**

```bash
git add workspace/prompts/pipeline/*.yaml
git commit -m "feat: add 5 pipeline YAML definitions"
```

### Task 4: 各步骤 Prompt 模板

**Files:**
- Create: `workspace/prompts/pipeline/polish/depai.md`
- Create: `workspace/prompts/pipeline/polish/prose.md`
- Create: `workspace/prompts/pipeline/polish/logic.md`
- Create: `workspace/prompts/pipeline/polish/rhythm.md`
- (共约 24 个 Prompt 模板文件)

- [ ] **Step 1: polish/depai.md**

```markdown
# 去AI味

请对以下文本进行去AI味处理：

## 原文
{{ file_content }}

## 要求
1. 删除以下AI高频套路词：「突然」「不禁」「心中一震」「莫名地」「不知为何」「忽然」
2. 删除冗余的连接词和过渡语：「然而」「与此同时」「值得注意的是」
3. 避免「开始」「逐渐」「仿佛」「似乎」等模糊化表达
4. 将被动句式改为主动句式
5. 保持原文的核心信息和逻辑结构
6. 输出的文字不应该让读者感觉到是AI生成的

请直接输出去AI味后的文本，不要添加任何说明。
```

- [ ] **Step 2: polish/prose.md**

```markdown
# 提升文笔

请对以下文本进行文笔提升：

## 原文
{{ previous_output }}

## 要求
1. 优化句式结构：长短句交替使用，避免连续短句或连续长句
2. 提升用词精准度：替换笼统的词汇为更具体、更有画面感的词汇
3. 适当增加感官描写（视觉、听觉、触觉、嗅觉），但不要过度
4. 减少「说」「想」「看」等基础动词的重复使用
5. 不要改变原文的核心情节和人物设定
6. 保持原文的叙事视角和语气

请直接输出去润色后的文本，不要添加任何说明。
```

- [ ] **Step 3: polish/logic.md**

```markdown
# 修正逻辑

请检查并修正以下文本中的逻辑问题：

## 原文
{{ previous_output }}

## 检查维度
1. 情节矛盾：是否有前后不一致的情节
2. 时间线冲突：时间顺序是否合理
3. 角色行为不一致：角色是否做出不符合其性格的行为
4. 设定偏移：是否偏离了作品的世界观设定
5. 因果关系：事件的因果链是否合理

## 要求
- 只修正确实存在的逻辑问题
- 不要改变原文的文风和语言特色
- 如果无需修正，直接返回原文

请直接输出修正后的文本，不要添加说明。
```

- [ ] **Step 4: polish/rhythm.md**

```markdown
# 优化节奏

请优化以下文本的叙事节奏：

## 原文
{{ previous_output }}

## 要求
1. 张弛有度：紧张情节和舒缓段落交替出现
2. 长短句交替：用短句加快节奏，用长句放慢节奏
3. 段落长度合理：紧张场景用短段落，描写场景用正常段落
4. 避免连续三个以上结构相似的句子
5. 保留原文的核心内容和情感基调

请直接输出节奏优化后的文本，不要添加任何说明。
```

- [ ] **Step 5: generate/context.md**

```markdown
# 整合上下文

## 当前章节
目标文件：{{ file_path }}
用户意图：{{ user_input }}

## 项目上下文
文风指南：{{ style_guide if exists }}
故事状态：{{ story_state if exists }}
近期上下文：{{ recent_context if exists }}

## 任务
请整合以上上下文信息，提取与当前章节相关的关键元素：
1. 当前故事进度和角色状态
2. 本章需要处理的情节线
3. 需要注意的设定约束

输出应为简洁的总结段落。
```

- [ ] **Step 6: generate/outline.md**

```markdown
# 大纲对齐

## 上一步整合的上下文
{{ previous_output }}

## 项目大纲
{{ outline if exists }}

## 任务
根据大纲确认本节需要覆盖哪些要点：
1. 列出本节应包含的关键情节节点
2. 标注哪些是必须包含的核心内容
3. 确认与前后章节的衔接点

输出大纲对齐后的写作指引。
```

- [ ] **Step 7: generate/draft.md**

```markdown
# 写作初稿

## 大纲指引
{{ previous_output }}

## 要求
请根据以上大纲指引和上下文，写出本节内容：
1. 按照大纲对齐中确定的要点展开写作
2. 保持与作品整体风格一致
3. 每节约 1500-2000 字
4. 注意章节结尾留悬念

请直接输出章节内容。
```

- [ ] **Step 8: generate/depai.md** (与 polish/depai.md 内容相同但引用上一步)

与 Task 4 Step 1 内容相同，区别是引用 `{{ previous_output }}`。

- [ ] **Step 9: rewrite/diagnose.md**

```markdown
# 诊断问题

请分析以下文本的主要问题：

## 原文
{{ file_content }}

## 分析维度
1. 文笔问题：句式是否单调、用词是否准确
2. 结构问题：段落组织是否合理、节奏是否得当
3. 逻辑问题：是否有矛盾或不合理之处
4. 可读性问题：是否清晰易懂

请输出诊断结果，列出最多3个最需要解决的问题，每个问题一句话。
```

- [ ] **Step 10: 其他模板文件**

按同样模式创建剩余的模板文件：
- `rewrite/draft.md` — 基于诊断结果重写
- `rewrite/depai.md` — 同 polish/depai.md
- `rewrite/logic.md` — 同 polish/logic.md
- `rewrite/rhythm.md` — 同 polish/rhythm.md
- `chat/understand.md` — 解析用户意图
- `chat/draft.md` — 根据理解执行
- `chat/validate.md` — 校验是否符合指令
- `extract/worldbuilding.md` — 提取世界观
- `extract/characters.md` — 提取角色
- `extract/plots.md` — 提取情节
- `extract/summary.md` — 生成摘要
- `generate/depai.md`、`generate/logic.md`、`generate/rhythm.md`

- [ ] **Step 11: Commit**

```bash
git add workspace/prompts/pipeline/
git commit -m "feat: add pipeline step prompt templates"
```

---

## Stage 3: 管线 API

### Task 5: 管线 API 路由

**Files:**
- Create: `backend/api/pipeline.py`

- [ ] **Step 1: 创建 API 路由，导入依赖**

```python
"""墨韵 - 管线引擎 API

端点：
  POST /api/pipeline/run         运行管线（SSE）
  GET  /api/pipeline/list        获取管线列表
  GET  /api/pipeline/{name}      获取管线详情（含 prompt）
  PUT  /api/pipeline/{name}      保存管线/步骤 prompt
  POST /api/pipeline/custom      创建自定义管线
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from backend.config import Settings, get_settings
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.file_ops import FileService
from backend.core.pipeline import PipelineRunner, PipelineError
from backend.schemas.common import ApiResponse
from backend.schemas.pipeline import (
    PipelineRunRequest,
    PipelineSaveRequest,
    CreatePipelineRequest,
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipeline"])
```

- [ ] **Step 2: POST /api/pipeline/run**

```python
@router.post("/pipeline/run")
async def run_pipeline(
    req: PipelineRunRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """运行管线（流式 SSE）"""
    event_bus = getattr(request.app.state, "event_bus", None)

    # 验证项目存在
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        from backend.core.exceptions import ProjectNotFoundError
        raise ProjectNotFoundError(req.project_id)

    # 初始化服务
    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    runner = PipelineRunner(settings.prompts_path, llm_service, file_service)

    async def _stream():
        task_id = f"pipeline-{req.pipeline}"

        if event_bus:
            await event_bus.publish("task", {
                "task_id": task_id,
                "status": "running",
                "name": req.pipeline,
            })

        try:
            async for event in runner.run(
                pipeline_name=req.pipeline,
                project_id=req.project_id,
                target_file=req.target_file,
                user_input=req.user_input,
                output_mode=req.output_mode,
                extra_vars=req.extra_vars,
            ):
                yield event
                if event_bus and event.get("event") in ("generation", "thinking", "done", "error"):
                    await event_bus.publish(event["event"], json.loads(event["data"]))

        except PipelineError as e:
            logger.error("管线运行失败: %s", e)
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(_stream())
```

- [ ] **Step 3: GET /api/pipeline/list**

```python
@router.get("/pipeline/list")
async def list_pipelines(
    settings: Settings = Depends(get_settings),
):
    """获取所有可用管线"""
    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    runner = PipelineRunner(settings.prompts_path, llm_service, file_service)

    pipelines = runner.list_pipelines()
    result = [
        {"name": p.name, "label": p.label, "steps": [{"id": s.id, "label": s.label} for s in p.steps], "source": "system"}
        for p in pipelines
    ]

    # 检查自定义管线
    custom_dir = settings.workspace_path / ".moyun" / "custom-pipelines"
    if custom_dir.exists():
        for f in sorted(custom_dir.glob("*.yaml")):
            try:
                p = runner.load_pipeline(f.stem)
                result.append({
                    "name": p.name, "label": p.label,
                    "steps": [{"id": s.id, "label": s.label} for s in p.steps],
                    "source": "custom",
                })
            except Exception:
                pass

    return ApiResponse.ok({"pipelines": result, "total": len(result)})
```

- [ ] **Step 4: GET /api/pipeline/{name}**

```python
@router.get("/pipeline/{name}")
async def get_pipeline(
    name: str,
    settings: Settings = Depends(get_settings),
):
    """获取管线详情"""
    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    runner = PipelineRunner(settings.prompts_path, llm_service, file_service)

    try:
        detail = runner.get_pipeline_detail(name)
        return ApiResponse.ok({"pipeline": detail})
    except PipelineError as e:
        from backend.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource="pipeline", identifier=name)
```

- [ ] **Step 5: PUT /api/pipeline/{name} 和 POST /api/pipeline/custom**

```python
@router.put("/pipeline/{name}")
async def save_pipeline(
    name: str,
    req: PipelineSaveRequest,
    settings: Settings = Depends(get_settings),
):
    """保存管线定义或步骤 prompt"""
    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    runner = PipelineRunner(settings.prompts_path, llm_service, file_service)

    if req.steps is not None:
        # 保存管线 YAML 定义
        runner.save_pipeline_yaml(name, req.label or name, req.steps)

    # 保存步骤 prompt 内容
    if req.steps:
        for step in req.steps:
            if step.get("prompt_content"):
                runner.save_step_prompt(name, step["id"], step["prompt_content"])

    return ApiResponse.ok(message=f"管线 {name} 已保存")


@router.post("/pipeline/custom")
async def create_custom_pipeline(
    req: CreatePipelineRequest,
    settings: Settings = Depends(get_settings),
):
    """创建自定义管线"""
    custom_dir = settings.workspace_path / ".moyun" / "custom-pipelines"
    custom_dir.mkdir(parents=True, exist_ok=True)

    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    runner = PipelineRunner(custom_dir, llm_service, file_service)

    # 保存 YAML
    runner.save_pipeline_yaml(req.name, req.label, req.steps)

    # 保存每步 prompt
    for step in req.steps:
        if step.get("prompt_content"):
            runner.save_step_prompt(req.name, step["id"], step["prompt_content"])

    return ApiResponse.ok(message=f"自定义管线 {req.name} 已创建")
```

- [ ] **Step 6: 注册路由到 main.py**

在 `backend/main.py` 中：

```python
# 在 import 中添加 pipeline
from backend.api import (
    ...
    pipeline,
)

# 在 include_router 中添加
app.include_router(pipeline.router, prefix="/api")
```

- [ ] **Step 7: Commit**

```bash
git add backend/api/pipeline.py backend/main.py
git commit -m "feat: add pipeline API endpoints (run/list/detail/save)"
```

### Task 6: 集成现有 Generate 端点

**Files:**
- Modify: `backend/api/generate.py`

- [ ] **Step 1: 修改 POST /api/generate 使用 PipelineRunner**

```python
# 在 generate 函数的 _stream() 中，替换现有的 LLM 调用逻辑为：

# 使用管线引擎运行
runner = PipelineRunner(settings.prompts_path, svc, file_service)
async for event in runner.run(
    pipeline_name="generate",
    project_id=req.project_id,
    target_file=req.file_path,
    user_input=req.extra_vars.get("user_prompt"),
    output_mode=req.mode,
    extra_vars=req.extra_vars,
    stop_event=_stop_signals.get(task_id),
):
    yield event
```

具体修改位置：将 `generate.py` 的 `_stream()` 中从 LLM 调用开始到保存结束的代码块，替换为使用 PipelineRunner 的调用。

- [ ] **Step 2: 修改 POST /api/chat 使用 PipelineRunner**

同上，将 chat 端点改为调用 `pipeline="chat"` 的管线。

- [ ] **Step 3: Commit**

```bash
git add backend/api/generate.py
git commit -m "refactor: integrate generate and chat endpoints with pipeline engine"
```

---

## Stage 4: 前端状态层

### Task 7: Pipeline Store

**Files:**
- Create: `frontend/src/stores/pipeline.ts`

- [ ] **Step 1: 创建 pipeline store**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export interface PipelineStepInfo {
  id: string
  label: string
}

export interface PipelineInfo {
  name: string
  label: string
  steps: PipelineStepInfo[]
  source: 'system' | 'custom'
}

export interface StepDetail {
  id: string
  label: string
  prompt_content: string
  fallback: string | null
}

export interface PipelineDetail {
  name: string
  label: string
  steps: StepDetail[]
}

export const usePipelineStore = defineStore('pipeline', () => {
  // 管线列表
  const pipelines = ref<PipelineInfo[]>([])
  const currentPipelineName = ref<string>('polish')
  const currentStepIndex = ref(0)

  // 当前选中的管线详情（含 prompt 内容）
  const currentDetail = ref<PipelineDetail | null>(null)

  const currentPipeline = computed(() =>
    pipelines.value.find(p => p.name === currentPipelineName.value)
  )

  const currentStep = computed(() => {
    if (!currentDetail.value) return null
    return currentDetail.value.steps[currentStepIndex.value] || null
  })

  const currentPromptContent = computed(() => {
    return currentStep.value?.prompt_content || ''
  })

  async function fetchPipelines() {
    try {
      const data = await api.get<{ pipelines: PipelineInfo[]; total: number }>('/pipeline/list')
      if (data?.pipelines) {
        pipelines.value = data.pipelines
      }
    } catch (e) {
      console.warn('获取管线列表失败:', e)
    }
  }

  async function fetchPipelineDetail(name: string) {
    try {
      const data = await api.get<{ pipeline: PipelineDetail }>(`/pipeline/${name}`)
      if (data?.pipeline) {
        currentDetail.value = data.pipeline
      }
    } catch (e) {
      console.warn('获取管线详情失败:', e)
    }
  }

  async function selectPipeline(name: string) {
    currentPipelineName.value = name
    currentStepIndex.value = 0
    await fetchPipelineDetail(name)
  }

  function selectStep(index: number) {
    if (currentDetail.value && index >= 0 && index < currentDetail.value.steps.length) {
      currentStepIndex.value = index
    }
  }

  async function saveStepPrompt(stepId: string, content: string) {
    if (!currentDetail.value) return
    try {
      await api.put(`/pipeline/${currentPipelineName.value}`, {
        name: currentPipelineName.value,
        steps: [{ id: stepId, prompt_content: content }],
      })
      // 更新本地状态
      const step = currentDetail.value.steps.find(s => s.id === stepId)
      if (step) step.prompt_content = content
    } catch (e) {
      console.warn('保存 prompt 失败:', e)
    }
  }

  async function createCustomPipeline(name: string, label: string, steps: { id: string; label: string; prompt_content: string }[]) {
    try {
      await api.post('/pipeline/custom', { name, label, steps })
      await fetchPipelines()
    } catch (e) {
      console.warn('创建管线失败:', e)
      throw e
    }
  }

  return {
    pipelines,
    currentPipelineName,
    currentStepIndex,
    currentDetail,
    currentPipeline,
    currentStep,
    currentPromptContent,
    fetchPipelines,
    fetchPipelineDetail,
    selectPipeline,
    selectStep,
    saveStepPrompt,
    createCustomPipeline,
  }
})
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/pipeline.ts
git commit -m "feat: add pipeline store with API integration"
```

### Task 8: Right Panel Store 更新

**Files:**
- Modify: `frontend/src/stores/rightPanel.ts`

- [ ] **Step 1: 更新 rightPanel store 增加管路编辑器状态**

在现有 `rightPanel.ts` 中新增字段：

```typescript
// 新增状态
const activePipelineTab = ref<'quick' | 'editor'>('quick')
const isPipelineRunning = ref(false)

// 新增 actions
function setPipelineTab(tab: 'quick' | 'editor') {
  activePipelineTab.value = tab
}

function setPipelineRunning(running: boolean) {
  isPipelineRunning.value = running
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/rightPanel.ts
git commit -m "feat: add pipeline tab state to rightPanel store"
```

---

## Stage 5: 前端右侧面板改造

### Task 9: 快捷（Prompt）面板改造

**Files:**
- Modify: `frontend/src/components/right-panel/PromptPanel.vue`
- Modify: `frontend/src/components/right-panel/RightPanel.vue`

- [ ] **Step 1: 改造 PromptPanel.vue 为「快捷」面板**

```
在模板中：
1. 顶部：管线下拉选择器（从 pipeline store 加载列表）
2. 第二步标签（可选步骤）：显示当前管线的步骤列表，点击切换
3. 中间：可编辑的 Prompt 文本框（绑定 currentStep.prompt_content）
4. 底部：运行按钮

新增功能：
- 选择管线时自动加载详情
- 编辑 prompt 后自动保存（防抖 500ms）
- 运行按钮调用 /api/pipeline/run
```

- [ ] **Step 2: 更新 RightPanel.vue Tab 结构**

```
将原有 Tab 列表改为：
- prompt → 改为 "快捷"（icon: ⚡）
- pipeline → 新增 "管线编辑"（icon: 🔧）
- story → 保留
- style → 保留
- execution → 保留

删除 context Tab。
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/right-panel/
git commit -m "feat: redesign right panel with quick pipeline tab"
```

### Task 10: 管线编辑面板

**Files:**
- Create: `frontend/src/components/right-panel/PipelineEditor.vue`

- [ ] **Step 1: 创建 PipelineEditor.vue**

```vue
<template>
  <div class="pipeline-editor">
    <!-- 管线选择器 -->
    <div class="editor-header">
      <a-select v-model:value="selectedPipeline" style="flex:1" @change="onPipelineChange">
        <a-select-option v-for="p in pipelines" :key="p.name" :value="p.name">
          {{ p.label }}
        </a-select-option>
      </a-select>
      <a-button @click="showNewPipelineModal">+ 新建</a-button>
    </div>

    <!-- 步骤列表（可拖拽排序） -->
    <div class="step-list">
      <div v-for="(step, index) in steps" :key="step.id"
           class="step-item" :class="{ active: index === editingStepIndex }"
           @click="editingStepIndex = index">
        <span class="step-drag">⠿</span>
        <span class="step-label">{{ step.label }}</span>
        <span class="step-id">{{ step.id }}</span>
        <a-button type="text" size="small" @click.stop="removeStep(index)">✕</a-button>
      </div>
      <a-button type="dashed" block @click="addStep">+ 添加步骤</a-button>
    </div>

    <!-- Prompt 编辑区 -->
    <div class="prompt-editor-section">
      <div class="editor-label">步骤 Prompt</div>
      <a-textarea v-model:value="editingPrompt" :auto-size="{ minRows: 8, maxRows: 16 }" />
      <div class="editor-actions">
        <a-button @click="savePrompt">保存</a-button>
        <a-button type="primary" @click="saveAll">保存全部</a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 实现管线编辑逻辑：
// - 选中管线 → 加载详情（含每步 prompt）
// - 点击步骤 → 编辑该步骤的 prompt
// - 添加/删除步骤 → 更新本地列表
// - 保存 → 调用 PUT /api/pipeline/{name}
// - 新建 → 调用 POST /api/pipeline/custom
</script>
```

- [ ] **Step 2: 将 PipelineEditor 注册到 RightPanel**

在 `RightPanel.vue` 中：

```vue
<PipelineEditor v-show="activeTab === 'pipeline'" />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/right-panel/PipelineEditor.vue
git commit -m "feat: add pipeline editor tab for step and prompt management"
```

---

## Stage 6: 前端工具栏改造

### Task 11: 精简工具栏

**Files:**
- Modify: `frontend/src/components/layout/AppHeader.vue`

- [ ] **Step 1: 修改工具栏按钮**

将现有 11 个按钮替换为 5 个：

```vue
<div class="toolbar-actions">
  <a-button type="primary" ghost @click="runPipeline('polish')">
    ✏️ 润色
  </a-button>
  <a-button type="primary" ghost @click="runPipeline('generate')">
    📝 生成
  </a-button>
  <a-button type="primary" ghost @click="runPipeline('rewrite')">
    📦 重写
  </a-button>
  <a-button type="primary" ghost @click="runPipeline('extract')">
    🌟 提取
  </a-button>
  <a-dropdown>
    <a-button>➕ 自定义</a-button>
    <template #overlay>
      <a-menu @click="handleCustomPipeline">
        <a-menu-item v-for="p in customPipelines" :key="p.name">
          {{ p.label }}
        </a-menu-item>
      </a-menu>
    </template>
  </a-dropdown>
</div>
```

- [ ] **Step 2: 实现 runPipeline 方法**

```typescript
async function runPipeline(name: string) {
  if (!projectStore.currentProject || !editorStore.currentFilePath) return
  const projectId = projectStore.currentProject.id
  const filePath = editorStore.currentFilePath

  // 切换到快捷标签
  rightPanelStore.setPipelineTab('quick')

  // 调用管线
  await fileGen.runPipeline(projectId, filePath, name)
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/AppHeader.vue
git commit -m "refactor: simplify toolbar to 5 pipeline buttons"
```

---

## Stage 7: 集成与清理

### Task 12: File Generation 适配管线

**Files:**
- Modify: `frontend/src/composables/useFileGeneration.ts`

- [ ] **Step 1: 添加 runPipeline 方法**

在 `useFileGeneration.ts` 中新增：

```typescript
async function runPipeline(projectId: string, filePath: string, pipelineName: string) {
  if (_isGenerating.value) return

  _isGenerating.value = true
  _currentPrompt.value = ''
  _abortController = new AbortController()

  try {
    editorStore.setCurrentFile(filePath)

    const response = await fetch('/api/pipeline/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pipeline: pipelineName,
        project_id: projectId,
        target_file: filePath,
        output_mode: pipelineName === 'generate' ? 'append' : 'overwrite',
      }),
      signal: _abortController.signal,
    })

    const reader = response.body?.getReader()
    if (!reader) throw new Error('无法读取响应流')

    await parseSSEStream(reader, (delta) => {
      editorStore.appendContent(delta)
    }, (prompt) => {
      _currentPrompt.value = prompt
      editorStore.setFilePrompt(filePath, prompt)
    })

  } catch (e: any) {
    if (e.name !== 'AbortError') throw e
  } finally {
    _isGenerating.value = false
    _abortController = null
  }
}
```

- [ ] **Step 2: 暴露 runPipeline**

```typescript
return {
  isGenerating: _isGenerating,
  currentPrompt: _currentPrompt,
  generateToFile,
  runPipeline,       // 新增
  cancelGeneration,
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useFileGeneration.ts
git commit -m "feat: add runPipeline method to file generation composable"
```

### Task 13: 清理旧代码

**Files:**
- Modify: 删除不需要的旧组件和代码

- [ ] **Step 1: 检查并删除不再使用的旧组件**

从 `App.vue` 中移除不再需要的旧模态框导入（如 `CompareModal` 等，如果已不再需要）。

从路由中移除不再需要的旧路由。

确保 `PromptPanel.vue` 中不再显示旧的模板选择器和无关按钮。

- [ ] **Step 2: 验证前后端集成**

```bash
# 重启后端
python -m uvicorn backend.main:app --reload

# 验证 API 可用
curl http://localhost:8000/api/pipeline/list

# 验证前端构建
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "chore: cleanup deprecated code after pipeline integration"
```

---

## 执行顺序

```
Stage 1: Pipeline 数据模型 + 引擎   → 可独立测试
Stage 2: YAML 定义 + Prompt 模板    → 可独立加载
Stage 3: Pipeline API               → 可通过 curl 测试
Stage 4: 前端状态层                  → 可独立于 UI
Stage 5: 右侧面板改造                → 可见可用
Stage 6: 工具栏精简                  → 可见可用
Stage 7: 集成 + 清理                → 完整可运行
```

每阶段完成后建议提交并快速验证，避免积压冲突。
