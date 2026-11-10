import { execFile } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

function localPrediction() {
  const run = promisify(execFile)
  const cwd = fileURLToPath(new URL('../', import.meta.url))
  const pending = new Map()

  function attach(server) {
    server.middlewares.use('/api/predictions', async (req, res) => {
      res.setHeader('Content-Type', 'application/json; charset=utf-8')
      res.setHeader('Cache-Control', 'no-store')
      if (req.method !== 'GET') {
        res.statusCode = 405
        res.setHeader('Allow', 'GET')
        res.end(JSON.stringify({ error: '请使用 GET 请求。' }))
        return
      }

      const day = new URL(req.url, 'http://127.0.0.1').searchParams.get('date')
      const args = ['-m', 'ml.web_prediction']
      if (day) args.push('--date', day)
      const key = day || 'next'
      try {
        let job = pending.get(key)
        if (!job) {
          job = run('python', args, {
            cwd,
            timeout: 180_000,
            windowsHide: true,
            env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
          }).finally(() => pending.delete(key))
          pending.set(key, job)
        }
        const { stdout } = await job
        res.end(JSON.stringify(JSON.parse(stdout)))
      } catch (error) {
        server.config.logger.error(error.stderr?.toString() || error.message)
        const detail = error.stderr?.toString().trim()
        res.statusCode = 503
        res.end(JSON.stringify({
          error: detail || '本地计算失败。请检查 Python 依赖、已校验数据和特码模型。',
        }))
      }
    })
  }

  return { name: 'local-prediction', configureServer: attach, configurePreviewServer: attach }
}

export default defineConfig({
  base: './',
  plugins: [vue(), localPrediction()],
})
