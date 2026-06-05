# LLM Endpoint 配置探针报告

- **Phase**: T3-D7.3c-b1
- **Mode**: real_run
- **LLM Called**: Yes

## 配置摘要 (Sanitized)

| 配置项 | 状态 |
|--------|------|
| Provider | ✅ 已配置 |
| Model | ✅ 已配置 |
| API Base | ✅ 已配置 |
| API Key | ✅ 已配置 |

## 测试结果

### models_endpoint
- **模型**: -
- **结果**: ❌ 失败
- **失败类型**: http_error
- **失败原因**: HTTP 401
- **可用模型数**: None

### chat_completion
- **模型**: custom_openai/agnes-2.0-flash
- **结果**: ❌ 失败
- **失败类型**: authentication_error
- **失败原因**: AuthenticationError

### chat_completion
- **模型**: agnes-2.0-flash
- **结果**: ❌ 失败
- **失败类型**: bad_request
- **失败原因**: BadRequestError

### chat_completion
- **模型**: openai/agnes-2.0-flash
- **结果**: ❌ 失败
- **失败类型**: authentication_error
- **失败原因**: AuthenticationError

### chat_completion
- **模型**: custom/agnes-2.0-flash
- **结果**: ❌ 失败
- **失败类型**: connection_error
- **失败原因**: APIConnectionError

## 摘要

- 测试完成，0/4 个候选模型成功
- 成功测试: 0/4
