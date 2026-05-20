## Summary

<!-- 简要描述这次 PR 做了什么，1-3 句话 -->



## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation update
- [ ] Other: __________



## Area

<!-- 这次改动影响哪个模块 -->

- [ ] Backend / API (`backend/`)
- [ ] Frontend (`frontend/src/`)
- [ ] Wiki / Documentation
- [ ] CI / DevOps
- [ ] Other: __________



## Checklist

<!-- 运行完以下命令后保留勾选状态 -->

- [ ] `backend/`: `python -m py_compile` 通过，无语法错误
- [ ] `backend/`: `pytest` 全部通过（新增测试用例）
- [ ] `frontend/`: `npm run build` 通过，无编译错误
- [ ] 不直接覆盖正式正文文件（只写 candidate 目录）
- [ ] 不通过 SSE 广播完整正文内容（敏感内容走加密）
- [ ] API 不直接暴露 `project_dir` / `path` 等路径参数
- [ ] `sec-*.md` 仍是单场景文件，不合并存储
- [ ] 行为变更同步更新 GitHub Wiki 相关页面
- [ ] 代码规范（raise 使用命名参数、类型注解完整）



## Commands Run

<!-- 记录本次验证用到的命令及结果 -->

```
# backend 语法检查
python -m py_compile backend/...

# backend 测试
pytest ...

# frontend 构建
npm run build
```




## Screenshots / Logs

<!-- 如有 UI 改动、报错截图或关键日志，贴在这里 -->



## Notes

<!-- 其他需要 reviewer 注意的事项，如：依赖变更、配置变更、向后兼容性等 -->



## Related Issue

<!-- 关联的 Issue（可选）：Closes # -->

