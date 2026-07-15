import { test, expect } from '@playwright/test'

test('home and health pages are reachable', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle('CampusAgent')
  await expect(page.getByRole('heading', { name: 'CampusAgent' })).toBeVisible()

  await page.goto('/health')
  await expect(page.getByRole('heading', { name: 'Health Check' })).toBeVisible()
  await expect(page.getByText('Status: OK')).toBeVisible()
})
