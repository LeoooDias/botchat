import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
	test: {
		globals: true,
		environment: 'jsdom',
		setupFiles: [],
		coverage: {
			provider: 'v8',
			reporter: ['text', 'json', 'html'],
			exclude: [
				'node_modules/',
				'build/',
				'.svelte-kit/'
			]
		}
	},
	resolve: {
		alias: {
			$lib: path.resolve('./src/lib')
		}
	}
});

