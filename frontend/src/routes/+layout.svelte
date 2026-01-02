<script lang="ts">
	import '../app.css';

	let { children } = $props();
	
	// Version injected at build time by Vite (defined in vite.config.ts)
	const appVersion = (globalThis as Record<string, unknown>).__APP_VERSION__ as string ?? 'dev';
</script>

<svelte:head>
	<title>botchat | many minds, no memory</title>
	<link rel="icon" type="image/x-icon" href="/favicon.ico" />
	<meta name="app-version" content={appVersion} />
</svelte:head>

{@render children()}
