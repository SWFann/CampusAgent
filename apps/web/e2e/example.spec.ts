// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { test, expect } from '@playwright/test'

test('has title', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle('CampusAgent')
})
