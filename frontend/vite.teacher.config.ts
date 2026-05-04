import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Vite config for TEACHER site (instructor dashboard)
// Build: npm run build:teacher
// Output: dist/teacher/index.html (CloudFront default root)

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const studentSiteUrl =
    process.env.VITE_STUDENT_SITE_URL ?? env.VITE_STUDENT_SITE_URL ?? ''

  const target = env.VITE_API_PROXY_TARGET?.trim()
  if (!target && command === 'serve') {
    throw new Error(
      'VITE_API_PROXY_TARGET is required for local dev. Set it in frontend/.env — see frontend/.env.example.',
    )
  }
  const proxyTarget = target || 'https://placeholder.invalid'

  return {
    plugins: [
      react(),
      {
        name: 'teacher-html-as-index',
        closeBundle() {
          const outDir = path.resolve(__dirname, 'dist/teacher')
          const teacherHtml = path.join(outDir, 'teacher.html')
          const indexHtml = path.join(outDir, 'index.html')
          if (fs.existsSync(teacherHtml)) {
            if (fs.existsSync(indexHtml)) fs.unlinkSync(indexHtml)
            fs.renameSync(teacherHtml, indexHtml)
          }
        },
      },
    ],
    define: {
      'import.meta.env.VITE_STUDENT_SITE_URL': JSON.stringify(studentSiteUrl),
    },
    build: {
      outDir: 'dist/teacher',
      emptyOutDir: true,
      rollupOptions: {
        input: path.resolve(__dirname, 'teacher.html'),
      },
    },
    server: {
      host: true,
      port: 5174,
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
