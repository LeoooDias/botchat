<script lang="ts">	import '../app.css';

	let { children } = $props();
	
	// Version injected at build time by Vite
	declare const __APP_VERSION__: string;
	const appVersion = __APP_VERSION__;
</script>

<svelte:head>
	<title>botchat | many minds, no memory</title>
	<link rel="icon" type="image/x-icon" href="/favicon.ico" />
	<meta name="app-version" content={appVersion} />
</svelte:head>

{@render children()}
