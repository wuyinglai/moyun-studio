/**
 * E2E 测试数据
 */

export const TEST_PROJECT = {
  name: 'E2E 真实LLM测试小说',

  settings: {
    genre: '近未来悬疑',
    conflict: '主角发现城市 AI 治理系统隐藏了对人的命运分级。',
  },

  characters: {
    protagonist: {
      name: '林澈',
      role: '前系统工程师',
      traits: '谨慎，有负罪感',
    },
    heroine: {
      name: '沈知夏',
      role: '调查记者',
      traits: '表面冷静，实际在隐藏自己的消息来源',
    },
  },

  coreScenes: ['废弃地铁站', '雨夜', '异常芯片', '黑塔编号'],

  initialText:
    '林澈站在废弃地铁站的入口，雨水顺着铁栏往下淌。广告屏每隔十秒闪一下，屏幕上却不是商业广告，而是一张三年前的寻人启事。\n\n他没有立刻进去。\n\n口袋里的芯片微微发烫，像是在提醒他，有人正等着他走进这条被封死的地下通道。',
} as const

/** 测试用 LLM 配置（DeepSeek 云模型）— API Key 从环境变量读取 */
export const TEST_LLM_CLOUD = {
  provider: 'openai-compatible',
  baseUrl: 'https://api.deepseek.com/v1',
  model: 'deepseek-v4-flash',
} as const

/** 测试用 LLM 配置（本地模型） */
export const TEST_LLM_LOCAL = {
  provider: 'openai-compatible',
  baseUrl: 'http://127.0.0.1:1234/v1',
  model: 'local-model',
} as const
