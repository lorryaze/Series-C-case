import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

/**
 * The demo runs on :3000 so compose, the README and the docs all point at one
 * URL. In dev, ``/api`` is proxied to the backend to avoid CORS entirely.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    server: {
      port: 3000,
      host: true,
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    preview: { port: 3000, host: true },
  };
});
