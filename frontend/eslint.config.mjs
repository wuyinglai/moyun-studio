// 墨韵前端 — ESLint 配置 (flat config)
// 使用方法: npx eslint .          (检查)
//          npx eslint . --fix    (自动修复)
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import pluginVue from "eslint-plugin-vue";
import vueParser from "vue-eslint-parser";

export default tseslint.config(
  // 基础推荐规则
  js.configs.recommended,

  // TypeScript 推荐规则
  ...tseslint.configs.recommended,

  // Vue 推荐规则（含模板解析）
  ...pluginVue.configs["flat/recommended"],

  // 全局 ignore
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "*.config.*",
    ],
  },

  // 全局配置
  {
    rules: {
      // ---------- 关闭的规则 ----------
      "no-console": "off",              // console.log 目前保留，后续逐步清理
      "vue/multi-word-component-names": "off", // 允许单词组件名（如 AppHeader）
      "@typescript-eslint/no-explicit-any": "warn", // any 类型先告警，最终改为 error

      // ---------- 开启的规则 ----------
      "no-debugger": "error",           // 禁止 debugger 进入提交
      "no-unused-vars": "off",          // 交给 TS 处理
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],                                // 未使用变量报错，_ 前缀除外
      "vue/block-lang": [
        "error",
        { script: { lang: "ts" } },     // 强制 <script lang="ts">
      ],
      "vue/no-unused-refs": "error",    // 未使用的 template ref 报错
      "vue/component-api-style": [
        "error",
        ["script-setup", "composition"], // 强制 Composition API
      ],
      "vue/require-default-prop": "warn", // 建议 props 给默认值
    },
  },

  // Vue 文件的特殊解析
  {
    files: ["**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        sourceType: "module",
      },
    },
  },
);
