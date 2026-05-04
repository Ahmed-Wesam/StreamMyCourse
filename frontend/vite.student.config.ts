import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Vite config for STUDENT site (view-only)
// Build: npm run build:student
// Output: dist/student/index.html (CloudFront default root; renamed from student.html)

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_PROXY_TARGET?.trim()
  if (!target && command === 'serve') {
    throw new Error(
      'VITE_API_PROXY_TARGET is required for local dev. Set it in frontend/.env — see frontend/.env.example.',
    )
  }
  const proxyTarget = target || 'https://placeholder.invalid'

  return {
    // Fast Refresh currently errors in this repo ("can't detect preamble") on Windows.
    // Disable it so local dev servers render reliably.
    plugins: [
      react({ fastRefresh: false }),
      {
        name: 'student-html-as-index',
        closeBundle() {
          const outDir = path.resolve(__dirname, 'dist/student')
          const studentHtml = path.join(outDir, 'student.html')
          const indexHtml = path.join(outDir, 'index.html')
          if (fs.existsSync(studentHtml)) {
            if (fs.existsSync(indexHtml)) fs.unlinkSync(indexHtml)
            fs.renameSync(studentHtml, indexHtml)
          }
        },
      },
    ],
    build: {
      outDir: 'dist/student',
      emptyOutDir: true,
      rollupOptions: {
        input: path.resolve(__dirname, 'student.html'),
      },
    },
    server: {
      host: true,
      port: 5173,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
