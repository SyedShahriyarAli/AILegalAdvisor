import { defineConfig, loadEnv } from 'vite'
import type { Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import fs from 'fs'

const DATA_DIR = path.resolve(__dirname, '..', 'backend', 'data');
const PDF_DIR = path.join(DATA_DIR, 'pdfs');

// ─── Vite Plugin: Serve PDFs from backend/data/pdfs ───
function servePdfsPlugin(): Plugin {
  return {
    name: 'serve-backend-pdfs',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url && req.url.startsWith('/pdfs/')) {
          try {
            const fileName = decodeURIComponent(
              req.url.replace('/pdfs/', '').split('#')[0].split('?')[0]
            );
            const filePath = path.join(PDF_DIR, fileName);

            if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
              const stat = fs.statSync(filePath);
              res.setHeader('Content-Type', 'application/pdf');
              res.setHeader('Content-Length', stat.size.toString());
              res.statusCode = 200;
              fs.createReadStream(filePath).pipe(res);
              return;
            } else {
              res.statusCode = 404;
              res.end('PDF not found');
              return;
            }
          } catch (err) {
            console.error('[PDF Serve] Error:', err);
          }
        }
        next();
      });
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // Never infer proxy target from VITE_API_BASE_URL — a typo there breaks every /api call in dev.
  const backendUrl =
    (env.VITE_DEV_BACKEND_PROXY || '').trim() || 'http://127.0.0.1:5000';

  return {
    plugins: [servePdfsPlugin(), react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
          configure(proxy) {
            proxy.on('error', (err, req) => {
              console.error('[vite /api proxy]', req?.method, req?.url, '→', err.message);
            });
          },
        }
      }
    }
  };
})
