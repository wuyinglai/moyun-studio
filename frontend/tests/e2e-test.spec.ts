import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BASE_URL = 'http://127.0.0.1:5175';
const WORKSPACE_PATH = process.env.MOYUN_WORKSPACE_PATH || path.join(__dirname, '..', '.e2e-workspace');

// 确保目录存在
const screenshotDir = path.join(__dirname, 'screenshots');
if (!fs.existsSync(screenshotDir)) {
  fs.mkdirSync(screenshotDir, { recursive: true });
}

if (!fs.existsSync(WORKSPACE_PATH)) {
  fs.mkdirSync(WORKSPACE_PATH, { recursive: true });
}

test.describe('墨韵 E2E 测试', () => {
  let projectId: string | null = null;

  test('测试1: 应用启动和空状态', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    
    // 等待页面关键元素出现
    await page.waitForSelector('body', { timeout: 15000 });
    await page.waitForTimeout(2000); // 给页面一些时间初始化

    // 检查页面元素
    await expect(page.locator('body')).toBeVisible();
    
    // 尝试查找导航按钮
    const openProjectBtn = page.locator('button', { hasText: '打开项目' });
    const newProjectBtn = page.locator('button', { hasText: '新建项目' });
    
    if (await openProjectBtn.isVisible()) {
      console.log('找到"打开项目"按钮');
    }
    if (await newProjectBtn.isVisible()) {
      console.log('找到"新建项目"按钮');
    }

    await page.screenshot({ path: path.join(screenshotDir, '01-home.png') });
    console.log('测试1完成');
  });

  test('测试2: 新建项目', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // 点击新建项目
    await page.getByText('新建项目').click();
    await page.waitForLoadState('networkidle');

    // 填写表单
    await page.getByLabel('项目名称').fill('测试项目');
    await page.getByLabel('作者').fill('测试作者');
    await page.getByLabel('类型').selectOption('玄幻');
    await page.getByRole('button', { name: '创建' }).click();

    await page.waitForNavigation();
    await page.waitForLoadState('networkidle');

    // 获取项目ID
    const url = page.url();
    const match = url.match(/\/project\/([^/]+)/);
    projectId = match ? match[1] : null;
    expect(projectId).not.toBeNull();

    await page.screenshot({ path: path.join(screenshotDir, '02-project-created.png') });
  });

  test('测试3: 专业工作台文件操作', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}`);
    await page.waitForLoadState('networkidle');

    // 创建测试文件
    await page.getByText('新建文件').click();
    await page.getByLabel('文件名').fill('test-chapter.md');
    await page.getByRole('button', { name: '确定' }).click();

    // 编辑内容
    await page.waitForSelector('textarea');
    await page.fill('textarea', '# 测试章节\n\n这是测试内容');
    await page.getByText('保存').click();
    await page.waitForTimeout(500);

    // 验证文件创建
    const filePath = path.join(WORKSPACE_PATH, 'projects', projectId, 'test-chapter.md');
    expect(fs.existsSync(filePath)).toBe(true);
    const content = fs.readFileSync(filePath, 'utf-8');
    expect(content).toContain('测试章节');

    await page.screenshot({ path: path.join(screenshotDir, '03-file-edit.png') });
  });

  test('测试4: 删除文件到回收站', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}`);
    await page.waitForLoadState('networkidle');

    // 删除文件
    await page.getByText('test-chapter.md').click({ button: 'right' });
    await page.getByText('删除').click();
    await page.getByRole('button', { name: '确认删除' }).click();

    // 验证回收站
    const trashPath = path.join(WORKSPACE_PATH, 'projects', projectId, '.trash');
    expect(fs.existsSync(trashPath)).toBe(true);

    await page.screenshot({ path: path.join(screenshotDir, '04-trash.png') });
  });

  test('测试5: 爽文模式访问', async ({ page }) => {
    if (!projectId) {
      test.skip();
    }

    await page.goto(`${BASE_URL}/project/${projectId}/lite`);
    await page.waitForLoadState('networkidle');

    // 检查爽文模式元素
    await expect(page.getByText('爽文模式')).toBeVisible();
    await expect(page.getByText('下一场景')).toBeVisible();

    await page.screenshot({ path: path.join(screenshotDir, '05-lite-mode.png') });
  });

  test.afterAll(async () => {
    // 清理测试数据
    if (projectId && fs.existsSync(path.join(WORKSPACE_PATH, 'projects', projectId))) {
      fs.rmSync(path.join(WORKSPACE_PATH, 'projects', projectId), { recursive: true, force: true });
    }
  });
});
