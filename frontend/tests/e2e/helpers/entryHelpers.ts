/**
 * 两个前端入口的导航辅助
 *
 * 主创作工作台：/ 和 /project/:projectId
 * 爽文模式：/lite 和 /project/:projectId/lite
 */

import { Page } from '@playwright/test'

/** 主创作工作台入口 */
export async function openMainEntry(page: Page): Promise<void> {
  await page.goto('/')
}

/** 爽文模式入口 */
export async function openLiteEntry(page: Page): Promise<void> {
  await page.goto('/lite')
}

/** 打开指定项目的专业模式 */
export async function openProjectMain(page: Page, projectId: string): Promise<void> {
  await page.goto(`/project/${projectId}`)
}

/** 打开指定项目的爽文模式 */
export async function openProjectLite(page: Page, projectId: string): Promise<void> {
  await page.goto(`/project/${projectId}/lite`)
}
