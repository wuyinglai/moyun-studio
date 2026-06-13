# Variant A: Inline Required Beats

Baseline strategy.

Required beats are placed inline in a normal prose-generation prompt:

```text
本场必须出现：第七层协议、银色芯片、残缺坐标、追踪者进入地下层。
```

Hypothesis:

This is concise and natural, but small models may treat the beat list as background instead of mandatory output constraints.
