import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/**
 * Vite dev serves `/` from root `index.html`, which loads the student entry.
 * Teacher builds use `teacher.html` only; this plugin makes dev match production
 * (instructor shell for `/` and client-side routes like `/courses/:id`).
 */
function teacherDevSpaEntryPlugin(): Plugin {
  return {
    name: 'teacher-dev-spa-entry',
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        if (req.method !== 'GET' && req.method !== 'HEAD') return next()
        const rawUrl = req.url
        if (!rawUrl) return next()
        const pathname = rawUrl.split('?')[0] ?? ''
        if (!pathname) return next()
        if (pathname.startsWith('/api')) return next()
        if (pathname.startsWith('/@')) return next()
        if (pathname.startsWith('/src/')) return next()
        if (pathname.startsWith('/node_modules/')) return next()
        if (pathname === '/teacher.html') return next()
        if (/\.[a-zA-Z0-9]+$/.test(pathname)) return next()
        const accept = req.headers.accept ?? ''
        if (!accept.includes('text/html')) return next()
        const q = rawUrl.includes('?') ? rawUrl.slice(rawUrl.indexOf('?')) : ''
        req.url = '/teacher.html' + q
        next()
      })
    },
  }
}

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
      teacherDevSpaEntryPlugin(),
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
