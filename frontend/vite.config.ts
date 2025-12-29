import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		host: '0.0.0.0',
		port: 3000,
		allowedHosts: [
			'botchat-frontend-887036129720.us-central1.run.app',
			'dev.botchat.ca',
			'localhost',
			'127.0.0.1'
		]
	}
});
