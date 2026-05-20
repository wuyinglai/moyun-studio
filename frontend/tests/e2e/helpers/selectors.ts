/**
 * E2E 统一选择器
 *
 * 所有 data-testid 集中管理，避免硬编码字符串散落在测试文件中。
 * 组件添加 data-testid 后在此处同步更新。
 */

export const SELECTORS = {
  // App root
  APP_ROOT: '[data-testid="app-root"]',

  // Main entry (专业模式)
  MAIN_ENTRY_ROOT: '[data-testid="main-entry-root"]',

  // Lite entry (爽文模式)
  LITE_ENTRY_ROOT: '[data-testid="lite-entry-root"]',

  // Project panel
  PROJECT_PANEL: '[data-testid="project-panel"]',
  PROJECT_LIST: '[data-testid="project-list"]',
  NEW_PROJECT_BUTTON: '[data-testid="new-project-button"]',

  // Create project modal
  CREATE_PROJECT_MODAL: '[data-testid="create-project-modal"]',
  CREATE_PROJECT_NAME_INPUT: '[data-testid="create-project-name-input"]',
  CREATE_PROJECT_SUBMIT: '[data-testid="create-project-submit"]',

  // File tree
  FILE_TREE: '[data-testid="file-tree"]',

  // Editor
  EDITOR_PANEL: '[data-testid="editor-panel"]',
  EDITOR_TEXTAREA: '[data-testid="editor-textarea"]',
  SAVE_FILE_BUTTON: '[data-testid="save-file-button"]',

  // Editor toolbar
  WRITE_NEXT_BUTTON: '[data-testid="write-next-button"]',
  REWRITE_BUTTON: '[data-testid="rewrite-button"]',
  POLISH_BUTTON: '[data-testid="polish-button"]',
  BATCH_GENERATE_BUTTON: '[data-testid="batch-generate-button"]',

  // Candidate panel
  CANDIDATE_PANEL: '[data-testid="candidate-panel"]',
  CANDIDATE_CONTENT: '[data-testid="candidate-content"]',
  CANDIDATE_ADOPT_BUTTON: '[data-testid="candidate-adopt-button"]',
  CANDIDATE_REJECT_BUTTON: '[data-testid="candidate-reject-button"]',

  // Settings
  SETTINGS_BUTTON: '[data-testid="settings-button"]',
  SETTINGS_MODAL: '[data-testid="settings-modal"]',
  LLM_PROVIDER_SELECT: '[data-testid="llm-provider-select"]',
  LLM_BASE_URL_INPUT: '[data-testid="llm-base-url-input"]',
  LLM_MODEL_INPUT: '[data-testid="llm-model-input"]',
  LLM_API_KEY_INPUT: '[data-testid="llm-api-key-input"]',
  LLM_TEST_BUTTON: '[data-testid="llm-test-button"]',

  // Task / SSE
  TASK_STATUS_PANEL: '[data-testid="task-status-panel"]',
  SSE_STATUS_INDICATOR: '[data-testid="sse-status-indicator"]',

  // Lite entry specific
  LITE_PROMPT_INPUT: '[data-testid="lite-prompt-input"]',
  LITE_GENERATE_BUTTON: '[data-testid="lite-generate-button"]',
  LITE_OUTPUT_PANEL: '[data-testid="lite-output-panel"]',
  LITE_ACCEPT_BUTTON: '[data-testid="lite-accept-button"]',
} as const

export type SelectorKey = keyof typeof SELECTORS
