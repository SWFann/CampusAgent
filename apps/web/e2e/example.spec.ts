import { test, expect } from '@playwright/test'

test('home and health pages are reachable', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/CampusAgent/)
  await expect(page.getByRole('heading', { name: 'CampusAgent' })).toBeVisible()

  await page.goto('/health')
  await expect(page.getByRole('heading', { name: '健康检查' })).toBeVisible()
  await expect(page.getByText('状态：正常')).toBeVisible()
})
