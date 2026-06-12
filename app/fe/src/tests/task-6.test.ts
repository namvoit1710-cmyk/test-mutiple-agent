import { test, expect } from '@playwright/experimental-ct-react'
import { render, screen } from '@testing-library/react'

import App from '../src/app'

test.describe('Task 6: Access Login Page (Authenticated)', () => {
  test('should redirect to /home when accessing /login if authenticated', async ({ page, mount }) => {
    // Arrange: Mount the app and set up authentication token
    await mount(<App />)
    await page.evaluate(() => {
      localStorage.setItem('authToken', 'fake-token')
    })

    // Act: Navigate to the login page
    await page.goto('/login')

    // Assert: Verify redirection to the home page
    await expect(page).toHaveURL('/home')
  })
})
