"""墨韵 - 配置管理

使用 pydantic-settings 管理所有配置，支持环境变量覆盖。
配置来源优先级：环境变量 > .env 文件 > 默认值
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── 服务配置 ───────────────────────────────────────────────
    host: str = Field(default="127.0.0.1", description="服务监听地址（默认仅本机访问）")
    port: int = Field(default=8000, description="服务监听端口")
    debug: bool = Field(default=False, description="调试模式")
    reload: bool = Field(default=False, description="热重载（仅开发环境）")

    # ─── 工作区配置 ─────────────────────────────────────────────
    workspace_path: Path = Field(
        default=Path("workspace"),
        description="工作区根目录（存放用户项目和自定义Prompt）",
    )
    projects_subdir: str = Field(default="projects", description="项目子目录名")
    prompts_subdir: str = Field(default="prompts", description="用户自定义Prompt子目录名")
    templates_subdir: str = Field(default="templates", description="模板文件子目录名")

    # ─── 系统Prompt配置 ────────────────────────────────────────
    system_prompts_path: Path = Field(
        default=Path("prompts"),
        description="系统默认Prompt模板目录（Git追踪）",
    )

    # ─── LLM 配置 ───────────────────────────────────────────────
    llm_provider: Literal["openai", "anthropic", "ollama", "custom"] = Field(
        default="openai", description="LLM 服务类型"
    )
    llm_api_key: str = Field(default="", description="LLM API Key")
    llm_api_base: str = Field(default="", description="LLM 服务地址")
    llm_model: str = Field(default="gpt-4", description="默认模型")
    llm_max_tokens: int = Field(default=16000, description="最大Token数")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度")
    llm_thinking: bool = Field(default=False, description="是否启用思考模式")

    # ─── 快照配置 ───────────────────────────────────────────────
    snapshot_max_versions: int = Field(default=20, description="最多保留版本数")
    snapshot_interval_seconds: int = Field(default=10, description="快照触发间隔（秒）")

    # ─── 任务队列配置 ────────────────────────────────────────────
    task_queue_max_concurrent: int = Field(default=1, description="最大并发任务数")
    auto_mode: Literal["L1", "L2"] = Field(default="L1", description="自动化等级")

    # ─── CORS 配置 ──────────────────────────────────────────────
    # 默认仅允许本地开发端口访问
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
        description="允许的跨域来源（仅本地开发）",
    )

    # ─── 安全配置 ───────────────────────────────────────────────
    allow_lan_access: bool = Field(
        default=False,
        description="是否允许局域网访问（默认 False，仅本机访问）",
    )

    # ─── 写入限制配置 ────────────────────────────────────────────
    max_file_write_size: int = Field(
        default=5 * 1024 * 1024,
        description="单个文件最大写入大小（字节，默认 5MB）",
    )
    max_candidate_size: int = Field(
        default=10 * 1024 * 1024,
        description="候选稿最大大小（字节，默认 10MB）",
    )

    # ─── 上下文记忆配置 ───────────────────────────────────────────
    recent_context_scene_limit: int = Field(
        default=15,
        description="recent-context 保留场景记忆数量（默认 15）",
    )

    # ─── 批量生成配置 ────────────────────────────────────────────
    batch_generate_max_count: int = Field(
        default=10,
        description="批量生成最大场景数（默认 10）",
    )

    @field_validator("workspace_path", mode="before")
    @classmethod
    def resolve_workspace(cls, v: str | Path) -> Path:
        return Path(v).resolve()

    @field_validator("host", mode="before")
    @classmethod
    def check_lan_access(cls, v: str) -> str:
        # 如果设置允许局域网访问，不强制绑定 127.0.0.1
        # 安全默认值仍然是 127.0.0.1
        return v

    @property
    def projects_path(self) -> Path:
        return self.workspace_path / self.projects_subdir

    @property
    def prompts_path(self) -> Path:
        return self.workspace_path / self.prompts_subdir

    @property
    def templates_path(self) -> Path:
        return self.workspace_path / self.templates_subdir


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取配置单例（带缓存）"""
    return Settings()
