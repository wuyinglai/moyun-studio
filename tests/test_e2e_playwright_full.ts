import { test, expect, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const BASE_URL = 'http://127.0.0.1:5175';
const WORKSPACE_PATH = process.env.MOYUN_WORKSPACE_PATH || path.join(__dirname, '..', '.e2e-workspace');

// 确保截图目录存在
const screenshotDir = path.join(__dirname, 'screenshots');
if (!fs.existsSync(screenshotDir)) {
  fs.mkdirSync(screenshotDir, { recursive: true });
}

async function takeScreenshot(page: Page, name: string) {
  await page.screenshot({ 
    path: path.join(screenshotDir, `${name}.png`),
    fullPage: true 
  });
}

async function waitForLoading(page: Page) {
  await page.waitForSelector('body', { state: 'visible' });
  await page.waitForTimeout(500);
}

test.describe('墨韵 E2E 用户操作测试', () => {
  let projectId: string | null = null;

  test.beforeAll(async () => {
    // 确保测试 workspace 存在
    if (!fs.existsSync(WORKSPACE_PATH)) {
      fs.mkdirSync(WORKSPACE_PATH, { recursive: true });
    }
  });

  // 测试用例 1：应用启动和空状态
  test('测试用例1: 应用启动和空状态', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForLoading(page);

    // 检查页面没有白屏
    await expect(page.locator('body')).toBeVisible();
    
    // 检查没有 console error
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // 检查顶部导航元素
    await expect(page.locator('button', { hasText: '打开项目' })).toBeVisible();
    await expect(page.locator('button', { hasText: '新建项目' })).toBeVisible();
    await expect(page.locator('button', { hasText: '设置' })).toBeVisible();

    // 打开设置弹窗
    await page.click('button', { hasText: '设置' });
    await expect(page.locator('.ant-modal-title', { hasText: '设置' })).toBeVisible();
    
    // 关闭设置弹窗
    await page.click('.ant-modal-close-icon');
    await expect(page.locator('.ant-modal-title', { hasText: '设置' })).not.toBeVisible();

    // 检查 LLM 状态提示
    const llmStatus = page.locator('[data-testid="llm-status"]');
    if (await llmStatus.isVisible()) {
      await expect(llmStatus).toHaveText(/未连接|未配置/);
    }

    await takeScreenshot(page, '01-home');
    await takeScreenshot(page, '02-settings');

    expect(errors).toEqual([]);
  });

  // 测试用例 2：爽文模式新建项目
  test('测试用例2: 爽文模式新建项目', async ({ page }) => {
    // 进入爽文模式
    await page.goto(`${BASE_URL}/lite`);
    await waitForLoading(page);

    // 检查开局卡
    const cards = page.locator('[data-testid="opening-card"]');
    await expect(cards).toHaveCount(5);

    // 点击换一批
    await page.click('button', { hasText: '换一批' });
    await page.waitForTimeout(1000);
    await expect(cards).toHaveCount(5);

    // 点击第一张开局卡
    await cards.first().click();
    await page.waitForNavigation();
    await waitForLoading(page);

    // 验证 URL
    const url = page.url();
    expect(url).toMatch(/\/project\/[^/]+\/lite/);
    projectId = url.match(/\/project\/([^/]+)\/lite/)?.[1] || null;
    expect(projectId).not.toBeNull();

    // 检查左侧作品名
    await expect(page.locator('[data-testid="project-title"]')).toBeVisible();

    // 检查中间编辑器
    await expect(page.locator('[data-testid="editor"]')).toBeVisible();

    // 检查右侧爽点卡
    await expect(page.locator('[data-testid="next-card"]')).toHaveCount(3);

    // 文件系统验证
    if (projectId) {
      const projectDir = path.join(WORKSPACE_PATH, 'projects', projectId);
      expect(fs.existsSync(projectDir)).toBe(true);
      
      const expectedFiles = ['project.json', 'story-state.md', 'recent-context.md'];
      for (const file of expectedFiles) {
        expect(fs.existsSync(path.join(projectDir, file))).toBe(true);
      }
      expect(fs.existsSync(path.join(projectDir, 'chapters'))).toBe(true);
    }

    await takeScreenshot(page, '03-lite-cards');
    await takeScreenshot(page, '04-lite-project-created');
  });

  // 测试用例 3：爽文模式选卡自动生成
  test('测试用例3: 爽文模式选卡自动生成', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}/lite`);
    await waitForLoading(page);

    // 选择第一张爽点卡
    const nextCards = page.locator('[data-testid="next-card"]');
    await nextCards.first().click();

    // 等待流式输出
    await page.waitForSelector('[data-testid="streaming-indicator"]');
    await page.waitForTimeout(5000); // 等待生成完成

    // 检查章节标签格式
    const chapterLabel = page.locator('[data-testid="chapter-label"]');
    await expect(chapterLabel).toHaveText(/第\d+卷 第\d+章 第\d+节/);

    // 文件检查
    if (projectId) {
      const chapterPath = path.join(WORKSPACE_PATH, 'projects', projectId, 'chapters', 'vol-01', 'ch-001');
      expect(fs.existsSync(chapterPath)).toBe(true);

      const secFiles = fs.readdirSync(chapterPath).filter(f => f.startsWith('sec-'));
      expect(secFiles.length).toBeGreaterThan(0);

      for (const secFile of secFiles) {
        const content = fs.readFileSync(path.join(chapterPath, secFile), 'utf-8');
        expect(content.length).toBeGreaterThan(10);
        expect(content).not.toContain('本节由系统在模型响应超时后生成临时草稿');
      }
    }

    await takeScreenshot(page, '05-lite-streaming');
    await takeScreenshot(page, '06-lite-generated-section');
  });

  // 测试用例 4：爽文模式章节规则
  test('测试用例4: 爽文模式章节规则', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}/lite`);
    await waitForLoading(page);

    // 模拟连续生成5节
    for (let i = 0; i < 5; i++) {
      const cards = page.locator('[data-testid="next-card"]');
      if (await cards.first().isVisible()) {
        await cards.first().click();
        await page.waitForTimeout(3000);
      }
    }

    // 检查章节号递增
    const chapterLabel = page.locator('[data-testid="chapter-label"]');
    const labelText = await chapterLabel.textContent();
    expect(labelText).toMatch(/第1卷 第(1|2)章 第(\d+)节/);
  });

  // 测试用例 5：爽文模式纠偏按钮
  test('测试用例5: 爽文模式纠偏按钮', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}/lite`);
    await waitForLoading(page);

    const buttons = ['重写这一章', '更爽一点', '更合理一点', '换个方向'];
    const chapterPath = path.join(WORKSPACE_PATH, 'projects', projectId, 'chapters', 'vol-01', 'ch-001', 'sec-001.md');
    const originalContent = fs.readFileSync(chapterPath, 'utf-8');

    for (const buttonText of buttons) {
      const button = page.locator('button', { hasText: buttonText });
      if (await button.isVisible()) {
        await button.click();
        await page.waitForTimeout(3000);
        
        // 检查按钮有 loading 状态
        await expect(button).toHaveClass(/ant-btn-loading/);
        
        // 等待生成完成
        await page.waitForTimeout(5000);
        
        // 检查内容变化
        const newContent = fs.readFileSync(chapterPath, 'utf-8');
        if (buttonText === '换个方向') {
          // 换个方向不修改当前章节内容，只刷新卡片
        } else {
          expect(newContent).not.toBe(originalContent);
        }
      }
    }
  });

  // 测试用例 6：专业模式切换
  test('测试用例6: 专业模式切换', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    // 从爽文模式切换到专业模式
    await page.goto(`${BASE_URL}/project/${projectId}/lite`);
    await waitForLoading(page);

    await page.click('button', { hasText: '专业模式' });
    await page.waitForNavigation();
    await waitForLoading(page);

    expect(page.url()).toBe(`${BASE_URL}/project/${projectId}`);

    // 切换回爽文模式
    await page.click('button', { hasText: '爽文模式' });
    await page.waitForNavigation();
    await waitForLoading(page);

    expect(page.url()).toBe(`${BASE_URL}/project/${projectId}/lite`);

    await takeScreenshot(page, '07-professional-mode');
    await takeScreenshot(page, '08-switch-back-lite');
  });

  // 测试用例 7：专业工作台基础编辑
  test('测试用例7: 专业工作台基础编辑', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}`);
    await waitForLoading(page);

    // 打开文件树
    await page.click('[data-testid="file-tree-toggle"]');
    
    // 新建文件夹
    await page.click('button', { hasText: '新建文件夹' });
    await page.fill('[data-testid="folder-name-input"]', 'test-folder');
    await page.click('button', { hasText: '确定' });
    await page.waitForTimeout(500);

    // 新建 Markdown 文件
    await page.click('button', { hasText: '新建文件' });
    await page.fill('[data-testid="file-name-input"]', 'test-file.md');
    await page.click('button', { hasText: '确定' });
    await page.waitForTimeout(500);

    // 输入内容
    await page.fill('[data-testid="editor-textarea"]', '# 测试文件\n\n这是测试内容');
    
    // 保存
    await page.click('button', { hasText: '保存' });
    await page.waitForTimeout(500);

    // 文件系统验证
    const testFile = path.join(WORKSPACE_PATH, 'projects', projectId, 'test-file.md');
    expect(fs.existsSync(testFile)).toBe(true);
    const content = fs.readFileSync(testFile, 'utf-8');
    expect(content).toContain('这是测试内容');

    // 重命名文件
    await page.click('[data-testid="file-tree-item-test-file.md"]');
    await page.click('button', { hasText: '重命名' });
    await page.fill('[data-testid="rename-input"]', 'renamed-file.md');
    await page.click('button', { hasText: '确定' });
    await page.waitForTimeout(500);

    expect(fs.existsSync(testFile)).toBe(false);
    expect(fs.existsSync(path.join(WORKSPACE_PATH, 'projects', projectId, 'renamed-file.md'))).toBe(true);

    // 删除文件
    await page.click('[data-testid="file-tree-item-renamed-file.md"]');
    await page.click('button', { hasText: '删除' });
    await page.click('button', { hasText: '确认删除' });
    await page.waitForTimeout(500);

    // 检查回收站
    const trashDir = path.join(WORKSPACE_PATH, 'projects', projectId, '.trash');
    expect(fs.existsSync(trashDir)).toBe(true);
  });

  // 测试用例 8：回收站
  test('测试用例8: 回收站', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}`);
    await waitForLoading(page);

    // 打开回收站
    await page.click('button', { hasText: '回收站' });
    
    // 检查回收站列表
    const trashItems = page.locator('[data-testid="trash-item"]');
    await expect(trashItems).toHaveCountGreaterThan(0);

    // 恢复文件
    await trashItems.first().click();
    await page.click('button', { hasText: '恢复' });
    await page.waitForTimeout(500);

    // 验证文件恢复
    const restoredFile = path.join(WORKSPACE_PATH, 'projects', projectId, 'renamed-file.md');
    expect(fs.existsSync(restoredFile)).toBe(true);

    // 再次删除并清空回收站
    await page.click('[data-testid="file-tree-item-renamed-file.md"]');
    await page.click('button', { hasText: '删除' });
    await page.click('button', { hasText: '确认删除' });
    await page.waitForTimeout(500);

    await page.click('button', { hasText: '清空回收站' });
    await page.click('button', { hasText: '确认清空' });
    await page.waitForTimeout(500);

    await expect(trashItems).toHaveCount(0);

    await takeScreenshot(page, '09-trash');
  });

  // 测试用例 9：快照、对比、恢复
  test('测试用例9: 快照、对比、恢复', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}`);
    await waitForLoading(page);

    // 打开章节文件
    await page.click('[data-testid="file-tree-item-chapters"]');
    await page.click('[data-testid="file-tree-item-vol-01"]');
    await page.click('[data-testid="file-tree-item-ch-001"]');
    
    const secFile = fs.readdirSync(path.join(WORKSPACE_PATH, 'projects', projectId, 'chapters', 'vol-01', 'ch-001'))
      .find(f => f.startsWith('sec-'));
    if (secFile) {
      await page.click(`[data-testid="file-tree-item-${secFile}"]`);
      await page.waitForTimeout(500);

      // 修改内容并保存两次
      const editor = page.locator('[data-testid="editor-textarea"]');
      await editor.fill('版本A内容');
      await page.click('button', { hasText: '保存' });
      await page.waitForTimeout(1000);

      await editor.fill('版本B内容');
      await page.click('button', { hasText: '保存' });
      await page.waitForTimeout(1000);

      // 打开对比弹窗
      await page.click('button', { hasText: '对比' });
      await page.waitForTimeout(500);

      // 选择两个快照
      const snapshots = page.locator('[data-testid="snapshot-item"]');
      if ((await snapshots.count()) >= 2) {
        await snapshots.nth(0).click();
        await snapshots.nth(1).click();
        
        // 检查差异显示
        await expect(page.locator('[data-testid="diff-view"]')).toBeVisible();

        // 恢复旧快照
        await page.click('button', { hasText: '恢复' });
        await page.waitForTimeout(500);

        // 验证恢复
        const restoredContent = fs.readFileSync(
          path.join(WORKSPACE_PATH, 'projects', projectId, 'chapters', 'vol-01', 'ch-001', secFile),
          'utf-8'
        );
        expect(restoredContent).toBe('版本A内容');
      }
    }

    await takeScreenshot(page, '10-compare');
  });

  // 测试用例 10：项目备份
  test('测试用例10: 项目备份', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}`);
    await waitForLoading(page);

    // 打开备份弹窗
    await page.click('button', { hasText: '备份' });
    await page.waitForTimeout(500);

    // 创建备份
    await page.fill('[data-testid="backup-description"]', '测试备份');
    await page.click('button', { hasText: '创建备份' });
    await page.waitForTimeout(2000);

    // 验证备份列表
    const backups = page.locator('[data-testid="backup-item"]');
    await expect(backups).toHaveCountGreaterThan(0);

    // 修改文件
    const testFile = path.join(WORKSPACE_PATH, 'projects', projectId, 'test-backup.md');
    fs.writeFileSync(testFile, '修改后的内容');

    // 恢复备份
    await backups.first().click();
    await page.click('button', { hasText: '恢复' });
    await page.click('button', { hasText: '确认恢复' });
    await page.waitForTimeout(2000);

    // 验证恢复
    expect(fs.existsSync(testFile)).toBe(false);

    // 删除备份
    await backups.first().click();
    await page.click('button', { hasText: '删除备份' });
    await page.click('button', { hasText: '确认删除' });
    await page.waitForTimeout(500);

    await takeScreenshot(page, '11-backup');
  });

  // 测试用例 11：质量审查
  test('测试用例11: 质量审查', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}`);
    await waitForLoading(page);

    // 打开质量审查弹窗
    await page.click('button', { hasText: '质量审查' });
    await page.waitForTimeout(500);

    // 选择当前章节
    await page.click('[data-testid="chapter-select"]');
    await page.click('[data-testid="chapter-option-1"]');

    // 点击审查
    await page.click('button', { hasText: '审查' });
    await page.waitForTimeout(5000);

    // 检查结果包含必要元素
    await expect(page.locator('[data-testid="review-summary"]')).toBeVisible();
    await expect(page.locator('[data-testid="review-score"]')).toBeVisible();
    await expect(page.locator('[data-testid="review-issues"]')).toBeVisible();
    await expect(page.locator('[data-testid="review-suggestions"]')).toBeVisible();

    await takeScreenshot(page, '12-quality-review');
  });

  // 测试用例 12：故事状态和近期上下文
  test('测试用例12: 故事状态和近期上下文', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}`);
    await waitForLoading(page);

    // 打开故事状态面板
    await page.click('[data-testid="story-state-tab"]');
    await page.waitForTimeout(500);

    // 点击更新
    const updateBtn = page.locator('button', { hasText: 'AI更新' });
    if (await updateBtn.isVisible()) {
      await updateBtn.click();
      await page.waitForTimeout(3000);
    }

    // 验证文件更新
    const storyStateFile = path.join(WORKSPACE_PATH, 'projects', projectId, 'story-state.md');
    expect(fs.existsSync(storyStateFile)).toBe(true);

    // 打开近期上下文面板
    await page.click('[data-testid="recent-context-tab"]');
    await page.waitForTimeout(500);

    // 添加上下文
    await page.fill('[data-testid="context-input"]', '测试上下文');
    await page.click('button', { hasText: '添加' });
    await page.waitForTimeout(500);

    // 验证文件更新
    const contextFile = path.join(WORKSPACE_PATH, 'projects', projectId, 'recent-context.md');
    expect(fs.existsSync(contextFile)).toBe(true);
    const content = fs.readFileSync(contextFile, 'utf-8');
    expect(content).toContain('测试上下文');

    // 删除上下文
    await page.click('[data-testid="context-delete-btn"]');
    await page.waitForTimeout(500);
  });

  // 测试用例 13：Prompt、管线、工作流
  test('测试用例13: Prompt、管线、工作流', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}`);
    await waitForLoading(page);

    // 打开 Prompt 面板
    await page.click('[data-testid="prompt-tab"]');
    await page.waitForTimeout(500);

    // 修改 Prompt
    const promptInput = page.locator('[data-testid="prompt-editor"]');
    if (await promptInput.isVisible()) {
      await promptInput.fill('自定义测试 Prompt');
      await page.click('button', { hasText: '保存' });
      await page.waitForTimeout(500);
    }

    // 打开管线编辑器
    await page.click('[data-testid="pipeline-tab"]');
    await page.waitForTimeout(500);

    // 新建自定义管线
    await page.click('button', { hasText: '新建管线' });
    await page.fill('[data-testid="pipeline-name"]', '测试管线');
    await page.click('button', { hasText: '保存' });
    await page.waitForTimeout(500);

    // 打开工作流面板
    await page.click('[data-testid="workflow-tab"]');
    await page.waitForTimeout(500);

    // 新建工作流
    await page.click('button', { hasText: '新建工作流' });
    await page.fill('[data-testid="workflow-name"]', '测试工作流');
    await page.click('button', { hasText: '保存' });
    await page.waitForTimeout(500);

    // 执行工作流
    const executeBtn = page.locator('button', { hasText: '执行' });
    if (await executeBtn.isVisible()) {
      await executeBtn.click();
      await page.waitForTimeout(3000);

      // 检查执行日志
      await expect(page.locator('[data-testid="execution-log"]')).toBeVisible();
    }
  });

  // 测试用例 14：错误与边界场景
  test('测试用例14: 错误与边界场景', async ({ page }) => {
    // 测试无项目状态
    await page.goto(`${BASE_URL}/project/not-exist`);
    await waitForLoading(page);

    // 检查错误提示
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('body')).not.toHaveText(/白屏|空白/);

    // 测试刷新页面恢复
    if (projectId) {
      await page.goto(`${BASE_URL}/project/${projectId}/lite`);
      await waitForLoading(page);
      
      await page.reload();
      await waitForLoading(page);

      expect(page.url()).toBe(`${BASE_URL}/project/${projectId}/lite`);
      await expect(page.locator('[data-testid="project-title"]')).toBeVisible();
    }
  });

  test.afterAll(async () => {
    // 清理测试数据
    if (projectId && fs.existsSync(path.join(WORKSPACE_PATH, 'projects', projectId))) {
      fs.rmSync(path.join(WORKSPACE_PATH, 'projects', projectId), { recursive: true, force: true });
    }
  });
});