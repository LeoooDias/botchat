<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { auth, isAuthenticated, authToken, getAuthHeaders } from '$lib/stores/auth';

	const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

	let isLoading = true;
	let subscriptionStatus: {
		status: string;
		is_subscribed: boolean;
		ends_at: string | null;
	} | null = null;
	let billingEnabled = false;
	let checkoutLoading = false;
	let portalLoading = false;
	let error: string | null = null;
	let successMessage: string | null = null;

	// Check URL params for success/cancel messages
	$: {
		const success = $page.url.searchParams.get('success');
		const canceled = $page.url.searchParams.get('canceled');
		if (success === 'true') {
			successMessage = 'Subscription successful! Welcome to botchat.';
			// Poll for status update (webhook may take a moment)
			if ($isAuthenticated) {
				pollForSubscription();
			}
		} else if (canceled === 'true') {
			error = 'Checkout was canceled.';
		}
	}

	// Poll for subscription status after checkout (webhooks may be delayed)
	async function pollForSubscription() {
		for (let i = 0; i < 10; i++) {
			await fetchSubscriptionStatus();
			if (subscriptionStatus?.is_subscribed) {
				successMessage = null; // Clear message once subscribed
				return;
			}
			await new Promise(r => setTimeout(r, 2000)); // Wait 2 seconds
		}
	}

	// Get user from auth store
	$: user = $auth.user;

	async function fetchBillingConfig() {
		try {
			const res = await fetch(`${API_BASE}/billing/config`);
			if (res.ok) {
				const config = await res.json();
				billingEnabled = config.enabled;
			}
		} catch {
			billingEnabled = false;
		}
	}

	async function fetchSubscriptionStatus() {
		if (!$authToken) {
			subscriptionStatus = null;
			return;
		}

		try {
			const res = await fetch(`${API_BASE}/billing/status`, {
				headers: getAuthHeaders()
			});
			if (res.ok) {
				subscriptionStatus = await res.json();
			} else {
				subscriptionStatus = null;
			}
		} catch {
			subscriptionStatus = null;
		}
	}

	async function startCheckout() {
		checkoutLoading = true;
		error = null;

		try {
			const res = await fetch(`${API_BASE}/billing/checkout`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...getAuthHeaders()
				},
				body: JSON.stringify({
					success_url: `${window.location.origin}/billing?success=true`,
					cancel_url: `${window.location.origin}/billing?canceled=true`
				})
			});

			if (res.ok) {
				const data = await res.json();
				// Redirect to Stripe Checkout
				window.location.href = data.checkout_url;
			} else {
				const errData = await res.json();
				error = errData.detail || 'Failed to start checkout';
			}
		} catch (e) {
			error = 'Failed to connect to server';
		} finally {
			checkoutLoading = false;
		}
	}

	async function openPortal() {
		portalLoading = true;
		error = null;

		try {
			const res = await fetch(`${API_BASE}/billing/portal`, {
				method: 'POST',
				headers: getAuthHeaders()
			});

			if (res.ok) {
				const data = await res.json();
				// Redirect to Stripe Customer Portal
				window.location.href = data.portal_url;
			} else {
				const errData = await res.json();
				error = errData.detail || 'Failed to open portal';
			}
		} catch (e) {
			error = 'Failed to connect to server';
		} finally {
			portalLoading = false;
		}
	}

	let theme: 'light' | 'dark' = 'light';

	function applyTheme(t: 'light' | 'dark') {
		if (t === 'dark') {
			document.documentElement.classList.add('dark');
		} else {
			document.documentElement.classList.remove('dark');
		}
	}

	onMount(async () => {
		// Load theme from localStorage
		const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
		if (savedTheme) {
			theme = savedTheme;
			applyTheme(savedTheme);
		} else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
			theme = 'dark';
			applyTheme('dark');
		}

		await fetchBillingConfig();
		if ($isAuthenticated) {
			await fetchSubscriptionStatus();
		}
		isLoading = false;
	});

	// Re-fetch subscription when auth changes
	$: if ($isAuthenticated && !isLoading) {
		fetchSubscriptionStatus();
	}

	function getStatusDisplay(status: string): { label: string; color: string } {
		switch (status) {
			case 'active':
				return { label: 'Active', color: 'text-green-600 dark:text-green-400' };
			case 'trialing':
				return { label: 'Free Trial', color: 'text-blue-600 dark:text-blue-400' };
			case 'canceled':
				return { label: 'Canceled', color: 'text-red-600 dark:text-red-400' };
			case 'past_due':
				return { label: 'Past Due', color: 'text-orange-600 dark:text-orange-400' };
			default:
				return { label: 'Free', color: 'text-gray-600 dark:text-gray-400' };
		}
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}
</script>

<svelte:head>
	<title>Billing | botchat | minds > memory</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
	<!-- Header -->
	<header class="bg-gradient-to-r from-blue-600 to-blue-700 dark:from-blue-800 dark:to-blue-900 text-white px-4 py-2 shadow">
		<div class="max-w-4xl mx-auto flex items-center justify-between">
			<a href="/" class="flex items-end gap-3 hover:opacity-80 transition">
				<span class="text-4xl font-bold leading-none">botchat</span>
				<span class="text-blue-100 text-xs leading-tight">many minds<br/>no memory</span>
			</a>
			<a
				href="/"
				class="text-sm text-blue-100 hover:text-white transition"
			>
				← Back to app
			</a>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-4xl mx-auto px-4 py-12">
		{#if isLoading}
			<div class="flex justify-center py-20">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
			</div>
		{:else if !billingEnabled}
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8 text-center">
				<h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">Billing Not Available</h1>
				<p class="text-gray-600 dark:text-gray-400">
					Billing is not configured for this instance. Please contact support.
				</p>
			</div>
		{:else if !$isAuthenticated}
			<!-- Not signed in -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8">
				<h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">Subscribe to botchat</h1>
				<p class="text-gray-600 dark:text-gray-400 mb-6">
					Sign in to manage your subscription and unlock unlimited access.
				</p>
				<a
					href="/"
					class="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition"
				>
					Sign in to continue
				</a>
			</div>
		{:else}
			<!-- Signed in -->
			{#if successMessage && !subscriptionStatus?.is_subscribed}
				<!-- Show success while waiting for webhook to update status -->
				<div class="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
					<p class="text-green-700 dark:text-green-400">{successMessage} Refreshing your subscription status...</p>
				</div>
			{/if}

			{#if error}
				<div class="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
					<p class="text-red-700 dark:text-red-400">{error}</p>
				</div>
			{/if}

			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
				<!-- Current Plan Section -->
				<div class="p-8 border-b border-gray-200 dark:border-gray-700">
					<h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Your Subscription</h1>
					<p class="text-gray-600 dark:text-gray-400 flex items-center gap-2">
						Signed in as 
						{#if user?.provider === 'github'}
							<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-full">
								<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
									<path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
								</svg>
								GitHub
							</span>
						{:else if user?.provider === 'google'}
							<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 text-gray-700 dark:text-gray-200 text-xs rounded-full">
								<svg class="w-3.5 h-3.5" viewBox="0 0 24 24">
									<path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
									<path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
									<path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
									<path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
								</svg>
								Google
							</span>
						{:else}
							<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 text-xs rounded-full">
								Dev
							</span>
						{/if}
						<span class="font-medium">{user?.email || user?.name}</span>
					</p>
				</div>

				<div class="p-8">
					{#if subscriptionStatus?.is_subscribed}
						<!-- Subscribed -->
						<div class="mb-8">
							<div class="flex items-center gap-3 mb-4">
								<svg class="w-8 h-8 text-amber-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
								</svg>
								<div>
									<h2 class="text-xl font-semibold text-gray-900 dark:text-white">botchat</h2>
									<p class={`text-sm font-medium ${getStatusDisplay(subscriptionStatus.status).color}`}>
										{getStatusDisplay(subscriptionStatus.status).label}
									</p>
								</div>
							</div>

							{#if subscriptionStatus.ends_at}
								<p class="text-sm text-gray-600 dark:text-gray-400">
									{#if subscriptionStatus.status === 'trialing'}
										Trial ends on {formatDate(subscriptionStatus.ends_at)}
									{:else if subscriptionStatus.status === 'canceled'}
										Access until {formatDate(subscriptionStatus.ends_at)}
									{:else}
										Next billing date: {formatDate(subscriptionStatus.ends_at)}
									{/if}
								</p>
							{/if}
						</div>

						<div class="space-y-3">
							<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Your benefits:</h3>
							<ul class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
								<li class="flex items-center gap-2">
									<span class="text-green-500">✓</span> Unlimited chats
								</li>
								<li class="flex items-center gap-2">
									<span class="text-green-500">✓</span> Up to 10 bots per chat
								</li>
								<li class="flex items-center gap-2">
									<span class="text-green-500">✓</span> 5,000 messages per month
								</li>
								<li class="flex items-center gap-2">
									<span class="text-green-500">✓</span> Bring your own AI keys (optional)
								</li>
							</ul>
						</div>

						<div class="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
							<button
								on:click={openPortal}
								disabled={portalLoading}
								class="px-6 py-3 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition disabled:opacity-50"
							>
								{portalLoading ? 'Loading...' : 'Manage Subscription'}
							</button>
							<p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
								Update payment method, view invoices, or cancel
							</p>
						</div>
					{:else}
						<!-- Not subscribed -->
						<div class="grid md:grid-cols-2 gap-8">
							<!-- Free Tier -->
							<div class="p-6 border border-gray-200 dark:border-gray-600 rounded-lg">
								<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Free</h2>
								<p class="text-3xl font-bold text-gray-900 dark:text-white mb-4">$0</p>
								<ul class="space-y-2 text-sm text-gray-600 dark:text-gray-400 mb-6">
									<li class="flex items-center gap-2">
										<span class="text-gray-400">•</span> 3 chats
									</li>
									<li class="flex items-center gap-2">
										<span class="text-gray-400">•</span> 3 bots per chat
									</li>
									<li class="flex items-center gap-2">
										<span class="text-gray-400">•</span> 100 messages per month
									</li>
									<li class="flex items-center gap-2">
										<span class="text-gray-400">•</span> Bring your own AI keys (optional)
									</li>
								</ul>
								<div class="py-3 text-center text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
									Current plan
								</div>
							</div>

							<!-- Pro Tier -->
							<div class="p-6 border-2 border-blue-500 rounded-lg relative">
								<div class="absolute -top-3 left-4 px-2 bg-blue-500 text-white text-xs font-medium rounded">
									7-day free trial
								</div>
								<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">botchat</h2>
								<p class="text-3xl font-bold text-gray-900 dark:text-white mb-1">
									<span class="text-lg text-gray-400 line-through font-normal mr-1">$9</span>$5 <span class="text-sm font-normal text-gray-500">CAD/month</span>
								</p>
								<p class="text-xs text-gray-500 dark:text-gray-400 mb-4">Cancel anytime</p>
								<ul class="space-y-2 text-sm text-gray-600 dark:text-gray-400 mb-6">
									<li class="flex items-center gap-2">
										<span class="text-green-500">✓</span> Unlimited chats
									</li>
									<li class="flex items-center gap-2">
										<span class="text-green-500">✓</span> 10 bots per chat
									</li>
									<li class="flex items-center gap-2">
										<span class="text-green-500">✓</span> 5,000 messages per month
									</li>
									<li class="flex items-center gap-2">
										<span class="text-green-500">✓</span> Bring your own AI keys (optional)
									</li>
								</ul>
								<button
									on:click={startCheckout}
									disabled={checkoutLoading}
									class="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
								>
									{checkoutLoading ? 'Loading...' : 'Start Free Trial'}
								</button>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</main>
</div>
