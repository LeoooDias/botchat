<script lang="ts">	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<title>botchat | minds > memory</title>
	<link rel="icon" type="image/x-icon" href="/favicon.ico" />
</svelte:head>

{@render children()}
