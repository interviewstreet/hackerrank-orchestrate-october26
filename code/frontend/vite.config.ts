import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
const proxy = { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false } };
export default defineConfig({ plugins: [react(), tailwindcss()], server: { proxy }, preview: { proxy } });
