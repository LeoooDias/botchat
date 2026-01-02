import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { readFileSync } from 'fs';

// Read version from package.json at build time
const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'));

export default defineConfig({
	plugins: [sveltekit()],
	define: {
		'__APP_VERSION__': JSON.stringify(pkg.version)
	},
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
