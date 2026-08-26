import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// Dev CORS is solved with a same-origin proxy: the SPA calls `/api/*` and Vite forwards it to the
// FastAPI backend (default http://127.0.0.1:8000) — so the backend needs no CORS change (ADR-0014).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const target = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000';
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ''),
        },
      },
    },
    preview: { port: 4173 },
  };
});
