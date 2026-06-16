import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  base: './',
  publicDir: 'public',
  // Bust the (non-hashed) data JSON cache on every build so deploys are picked
  // up immediately instead of serving a browser-cached older dataset.
  define: { __BUILD__: JSON.stringify(String(Date.now())) },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
