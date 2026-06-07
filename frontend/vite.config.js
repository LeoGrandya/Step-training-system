import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { readFileSync, existsSync } from 'node:fs';
import { extname, join, resolve } from 'node:path';

const siteRoot = resolve(__dirname, '../site');
const htmlFiles = new Set([
  'home.html',
  'loading.html',
  'product.html',
  'report.html',
  'settings.html',
  'team.html',
]);

function contentType(path) {
  const ext = extname(path).toLowerCase();
  if (ext === '.css') return 'text/css; charset=utf-8';
  if (ext === '.js') return 'application/javascript; charset=utf-8';
  if (ext === '.svg') return 'image/svg+xml';
  if (ext === '.png') return 'image/png';
  if (ext === '.jpg' || ext === '.jpeg') return 'image/jpeg';
  if (ext === '.mp4') return 'video/mp4';
  return 'application/octet-stream';
}

function withBase(html) {
  if (html.includes('<base href="/">')) return html;
  return html.replace(/<head>/i, '<head>\n    <base href="/">');
}

export default defineConfig({
  base: '/spa/',
  plugins: [
    vue(),
    {
      name: 'serve-legacy-html',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const url = decodeURIComponent((req.url || '').split('?')[0]);
          const legacyMatch = url.match(/^\/legacy-html\/([^/]+\.html)$/);
          const rootMatch = url.match(/^\/([^/]+\.html)$/);
          const htmlName = legacyMatch?.[1] || rootMatch?.[1];

          if (htmlName && htmlFiles.has(htmlName)) {
            const htmlPath = join(siteRoot, htmlName);
            if (existsSync(htmlPath)) {
              res.setHeader('Content-Type', 'text/html; charset=utf-8');
              res.end(withBase(readFileSync(htmlPath, 'utf8')));
              return;
            }
          }

          if (url.startsWith('/assets/')) {
            const assetPath = join(siteRoot, url.slice(1));
            if (existsSync(assetPath)) {
              res.setHeader('Content-Type', contentType(assetPath));
              res.end(readFileSync(assetPath));
              return;
            }
          }

          next();
        });
      },
    },
  ],
  build: {
    outDir: resolve(__dirname, '../web_1/static/spa'),
    emptyOutDir: true,
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
});
