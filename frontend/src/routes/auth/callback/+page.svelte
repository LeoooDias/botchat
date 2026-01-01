<!--
	OAuth Callback Page
	
	Handles redirect from GitHub/Google/Apple/Microsoft OAuth.
	Extracts code from URL, exchanges for JWT, redirects to main app.
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { completeOAuthFlow, authError, authLoading } from '$lib/stores/auth';

	let message = 'Completing sign in...';

	onMount(async () => {
		const code = $page.url.searchParams.get('code');
		const error = $page.url.searchParams.get('error');
		const errorDescription = $page.url.searchParams.get('error_description');

		if (error) {
			message = errorDescription || error || 'Authentication was cancelled';
			setTimeout(() => goto('/'), 3000);
			return;
		}

		if (!code) {
			message = 'No authorization code received';
			setTimeout(() => goto('/'), 3000);
			return;
		}

		const success = await completeOAuthFlow(code);
		
		if (success) {
			message = 'Sign in successful! Redirecting...';
			setTimeout(() => goto('/'), 500);
		} else {
			message = $authError || 'Authentication failed';
			setTimeout(() => goto('/'), 3000);
		}
	});
</script>

<svelte:head>
	<title>Signing in... | botchat</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
	<div class="text-center p-8">
		{#if $authLoading}
			<div class="mb-4">
				<svg class="animate-spin h-8 w-8 mx-auto text-blue-600" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
				</svg>
			</div>
		{:else if $authError}
			<div class="mb-4">
				<svg class="h-8 w-8 mx-auto text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
				</svg>
			</div>
		{:else}
			<div class="mb-4">
				<svg class="h-8 w-8 mx-auto text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
				</svg>
			</div>
		{/if}
		
		<p class="text-gray-700 dark:text-gray-300">{message}</p>
		
		<a 
			href="/" 
			class="mt-4 inline-block text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
		>
			← Back to botchat
		</a>
	</div>
</div>
