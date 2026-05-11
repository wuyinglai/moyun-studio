"""墨韵 - Prompt引擎服务实现

封装Prompt模板加载和渲染。
"""

import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from backend.config import get_settings
from backend.services.base import PromptEngineInterface


class PromptEngineService(PromptEngineInterface):
    """Prompt引擎服务实现"""

    REFERENCE_PATTERN = __import__("re").compile(r"@\{([^}]+)\}")

    def __init__(self):
        self.settings = get_settings()
        self.prompts_path = self.settings.prompts_path
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_path)),
            autoescape=False,
        )
        self._file_service = None

    def set_file_service(self, file_service) -> None:
        """设置文件服务"""
        self._file_service = file_service

    async def render(
        self,
        category: str,
        template_type: str,
        variables: dict[str, Any]
    ) -> str:
        """渲染模板"""
        # 解析引用
        resolved = await self._resolve_variables(variables)

        # 加载模板
        template_path = f"{category}/{template_type}/main.md"
        try:
            template = self.env.get_template(template_path)
        except Exception:
            raise Exception(f"模板不存在: {template_path}")

        return template.render(**resolved)

    async def _resolve_variables(self, variables: dict[str, Any]) -> dict[str, Any]:
        """解析变量中的引用"""
        if self._file_service is None:
            return variables

        resolved = {}
        for key, value in variables.items():
            if isinstance(value, str) and self.REFERENCE_PATTERN.match(value):
                file_path = value[2:-1]
                try:
                    content, _ = await self._file_service.read_file(file_path)
                    resolved[key] = content
                except Exception:
                    resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = await self._resolve_variables(value)
            elif isinstance(value, list):
                resolved_list = []
                for v in value:
                    if isinstance(v, str) and self.REFERENCE_PATTERN.match(v):
                        file_path = v[2:-1]
                        try:
                            content, _ = await self._file_service.read_file(file_path)
                            resolved_list.append(content)
                        except Exception:
                            resolved_list.append(v)
                    else:
                        resolved_list.append(v)
                resolved[key] = resolved_list
            else:
                resolved[key] = value

        return resolved

    def list_templates(self, category: str | None = None) -> list[dict[str, str]]:
        """列出可用模板"""
        templates = []

        base_path = self.prompts_path
        if category:
            base_path = base_path / category

        if not base_path.exists():
            return templates

        for cat_dir in sorted(base_path.iterdir()):
            if not cat_dir.is_dir():
                continue
            cat_name = cat_dir.name

            for template_dir in sorted(cat_dir.iterdir()):
                if not template_dir.is_dir():
                    continue
                template_name = template_dir.name
                main_file = template_dir / "main.md"

                if main_file.exists():
                    # 读取模板描述
                    description = ""
                    readme_file = template_dir / "README.md"
                    if readme_file.exists():
                        description = readme_file.read_text(encoding="utf-8").strip()

                    templates.append({
                        "category": cat_name,
                        "type": template_name,
                        "path": f"{cat_name}/{template_name}/main.md",
                        "description": description,
                    })

        return templates

    def get_template(self, category: str, template_type: str) -> dict[str, Any]:
        """获取模板信息"""
        template_path = self.prompts_path / category / template_type

        if not template_path.exists():
            raise Exception(f"模板不存在: {category}/{template_type}")

        main_file = template_path / "main.md"
        if not main_file.exists():
            raise Exception(f"模板文件不存在: {main_file}")

        content = main_file.read_text(encoding="utf-8")

        # 解析 frontmatter（如果有）
        description = ""
        readme_file = template_path / "README.md"
        if readme_file.exists():
            description = readme_file.read_text(encoding="utf-8").strip()

        return {
            "category": category,
            "type": template_type,
            "path": f"{category}/{template_type}/main.md",
            "content": content,
            "description": description,
        }

    async def save_template(
        self,
        category: str,
        template_type: str,
        content: str,
        description: str | None = None
    ) -> None:
        """保存模板"""
        template_path = self.prompts_path / category / template_type
        template_path.mkdir(parents=True, exist_ok=True)

        main_file = template_path / "main.md"
        async with __import__("aiofiles").open(main_file, "w", encoding="utf-8") as f:
            await f.write(content)

        if description:
            readme_file = template_path / "README.md"
            async with __import__("aiofiles").open(readme_file, "w", encoding="utf-8") as f:
                await f.write(description)

    def estimate_tokens(self, text: str) -> int:
        """估算token数"""
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except Exception:
            return len(text) // 4
