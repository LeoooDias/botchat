<!--
	LoginButton Component
	
	Shows user avatar/name when authenticated, or "Sign in" link when not.
	The actual sign-in buttons are in SignInModal.
-->
<script lang="ts">
	import { auth, isAuthenticated, currentUser, authLoading, logout } from '$lib/stores/auth';
	import { onMount, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher<{ openSignIn: void }>();

	// Check token expiry periodically
	onMount(() => {
		const interval = setInterval(() => {
			auth.checkExpiry();
		}, 60000); // Check every minute
		
		return () => clearInterval(interval);
	});

	function handleSignInClick() {
		dispatch('openSignIn');
	}

	function handleLogout() {
		logout();
	}
</script>

{#if $authLoading}
	<span class="text-sm text-blue-100">Loading...</span>
{:else if $isAuthenticated && $currentUser}
	<!-- Authenticated: Show user info and logout -->
	<div class="flex items-center gap-2">
		<button
			on:click={handleLogout}
			class="text-sm text-blue-100 hover:text-white underline"
		>
			Sign out
		</button>
		{#if $currentUser.avatar}
			<img 
				src={$currentUser.avatar} 
				alt={$currentUser.name || 'User avatar'} 
				class="w-7 h-7 rounded-full object-cover border border-blue-400"
				referrerpolicy="no-referrer"
			/>
		{/if}
		<span class="text-sm text-white hidden sm:inline">
			{$currentUser.name || $currentUser.email || 'User'}
		</span>
	</div>
{:else}
	<!-- Not authenticated: Show sign in link -->
	<button
		on:click={handleSignInClick}
		class="text-sm hover:text-blue-100 transition-colors"
	>
		Sign in
	</button>
{/if}
