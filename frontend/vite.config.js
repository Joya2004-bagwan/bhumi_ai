import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 4000,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/models': { target: 'http://localhost:8000', changeOrigin: true },
      '/upload': { target: 'http://localhost:8000', changeOrigin: true },
      '/segment': { target: 'http://localhost:8000', changeOrigin: true },
      '/boundaries': { target: 'http://localhost:8000', changeOrigin: true },
      '/images': { target: 'http://localhost:8000', changeOrigin: true },
      '/masks': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
