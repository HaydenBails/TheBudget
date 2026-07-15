import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Local-first: dev server binds to localhost only.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
  },
  preview: {
    host: '127.0.0.1',
  },
});
