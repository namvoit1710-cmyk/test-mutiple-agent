// Vitest global setup — loaded via `setupFiles` in vitest.config.ts.
// Registers jest-dom matchers (toBeInTheDocument, toHaveTextContent, ...) and
// cleans up the rendered React tree after every test so tests stay isolated.
import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
})
