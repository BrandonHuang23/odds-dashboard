import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			// Proxy REST API calls to FastAPI backend during development
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true,
			},
			// Proxy WebSocket connections to FastAPI backend
			'/ws': {
				target: 'ws://localhost:8000',
				ws: true,
			},
		},
	},
});
