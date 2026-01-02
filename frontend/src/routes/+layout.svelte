<script lang="ts">
	import '../app.css';

	let { children } = $props();
	
	// Version injected at build time by Vite (defined in vite.config.ts)
	// @ts-ignore - __APP_VERSION__ is injected by Vite at build time
	const appVersion: string = __APP_VERSION__;
</script>

<svelte:head>
	<title>botchat | many minds, no memory</title>
	<link rel="icon" type="image/x-icon" href="/favicon.ico" />
	<meta name="app-version" content={appVersion} />
</svelte:head>

{@render children()}
