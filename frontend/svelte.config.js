import adapterAuto from '@sveltejs/adapter-auto';
import adapterNode from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// Use Node adapter for Docker builds, auto adapter otherwise
const adapter = process.env.ADAPTER === 'node' ? adapterNode() : adapterAuto();

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// Uses Node adapter when ADAPTER=node (Docker), otherwise adapter-auto for dev/Vercel
		adapter
	}
};

export default config;
