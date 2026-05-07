import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.{ts,tsx}'],
    passWithNoTests: false,
    coverage: {
      /** Only collect when running `vitest run --coverage` (no cost on plain `npm run test`). */
      enabled: false,
      provider: 'v8',
      reporter: ['text-summary', 'json-summary'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/**/*-main.tsx',
        'src/**/*.d.ts',
        '**/node_modules/**',
      ],
    },
  },
})
