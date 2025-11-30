import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [svelte()],
  server: {
    proxy: { '/api': { target: 'http://localhost:3000', changeOrigin: true, secure: false } },
  },
});
