# Agnes MCP 接入

本项目提供一个独立的 stdio MCP server：

```text
scripts/agnes_mcp_server.py
```

它通过 Agnes 的 OpenAI-compatible API 提供三个工具：

- `agnes_chat`：文本生成，默认模型 `agnes-2.0-flash`
- `agnes_image_generate`：图片生成，默认模型 `agnes-image-2.1-flash`
- `agnes_video_generate`：视频生成，默认接口 `/videos`

## 安全规则

不要把 API Key 写入代码、文档、Git 或截图。运行时通过环境变量传入：

```powershell
setx AGNES_API_KEY "your-agnes-api-key"
```

重启终端后生效。也可以在 MCP client 的本地配置里通过 `env` 注入。

## MCP Client 配置示例

把路径替换为你的本地仓库路径：

```json
{
  "mcpServers": {
    "agnes": {
      "command": "python",
      "args": ["D:/newmoyun/scripts/agnes_mcp_server.py"],
      "env": {
        "AGNES_API_KEY": "your-agnes-api-key",
        "AGNES_BASE_URL": "https://apihub.agnes-ai.com/v1",
        "AGNES_LLM_MODEL": "agnes-2.0-flash",
        "AGNES_IMAGE_MODEL": "agnes-image-2.1-flash"
      }
    }
  }
}
```

## 工具参数

### agnes_chat

```json
{
  "prompt": "写一个 200 字的开场",
  "system": "你是小说创作助手",
  "temperature": 0.7,
  "max_tokens": 2000
}
```

也支持直接传 OpenAI 格式的 `messages`：

```json
{
  "messages": [
    { "role": "system", "content": "你是小说创作助手" },
    { "role": "user", "content": "写一个 200 字的开场" }
  ]
}
```

### agnes_image_generate

```json
{
  "prompt": "中国玄幻小说封面，少年剑修，云海，电影感",
  "size": "1024x1024",
  "n": 1
}
```

### agnes_video_generate

```json
{
  "prompt": "云海中的仙山缓慢推进，电影镜头",
  "duration": 5,
  "aspect_ratio": "16:9"
}
```

如果 Agnes 的视频接口需要额外字段，可放入 `extra`：

```json
{
  "prompt": "云海中的仙山缓慢推进，电影镜头",
  "extra": {
    "callback_url": "https://example.com/callback"
  }
}
```

## 本地烟测

不需要 API Key 的工具列表测试：

```powershell
'{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python scripts/agnes_mcp_server.py
```

真实调用测试需要先设置 `AGNES_API_KEY`。
