# Variant C: Self-check After Draft

The prompt asks the model to silently check whether all required beats are included before final output:

```text
生成正文前，请在内部确认是否包含所有 required beats。
如果任一项缺失，请重写后再输出最终正文。
最终只输出正文，不输出检查过程。
```

Hypothesis:

Self-check may reduce omissions without changing the visible output format, but the model may still ignore the hidden check.
