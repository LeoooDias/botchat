<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fly, fade } from 'svelte/transition';

	export let isOpen = false;
	export let title = 'Alert';
	export let message = '';
	export let type: 'info' | 'warning' | 'error' | 'success' = 'info';
	export let confirmText = 'OK';
	export let cancelText = 'Cancel';
	export let showCancel = false;

	const dispatch = createEventDispatcher<{ 
		confirm: void; 
		cancel: void;
		close: void;
	}>();

	function handleConfirm() {
		dispatch('confirm');
		dispatch('close');
	}

	function handleCancel() {
		dispatch('cancel');
		dispatch('close');
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			if (showCancel) {
				handleCancel();
			} else {
				handleConfirm();
			}
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (!isOpen) return;
		
		if (e.key === 'Escape') {
			if (showCancel) {
				handleCancel();
			} else {
				handleConfirm();
			}
		} else if (e.key === 'Enter') {
			e.preventDefault();
			handleConfirm();
		}
	}

	const icons = {
		info: '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" /></svg>',
		warning: '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>',
		error: '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>',
		success: '<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>'
	};

	const colors = {
		info: 'bg-blue-500',
		warning: 'bg-amber-500',
		error: 'bg-red-500',
		success: 'bg-green-500'
	};
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
	<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-black/60 z-[100] flex items-center justify-center p-4"
		on:click={handleBackdropClick}
		role="presentation"
		transition:fade={{ duration: 150 }}
	>
		<!-- Modal -->
		<div
			class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden"
			role="dialog"
			aria-modal="true"
			aria-labelledby="alert-title"
			transition:fly={{ y: 20, duration: 200 }}
		>
			<!-- Header with icon -->
			<div class="flex items-center gap-3 px-5 py-4 border-b border-gray-200 dark:border-gray-700">
				<span class="flex-shrink-0 {type === 'info' ? 'text-blue-500' : type === 'warning' ? 'text-amber-500' : type === 'error' ? 'text-red-500' : 'text-green-500'}">
					{@html icons[type]}
				</span>
				<h2 id="alert-title" class="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
			</div>

			<!-- Message -->
			<div class="px-5 py-4">
				<p class="text-gray-600 dark:text-gray-300 whitespace-pre-line">{message}</p>
			</div>

			<!-- Buttons -->
			<div class="flex gap-3 px-5 py-4 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700">
				{#if showCancel}
					<button
						on:click={handleCancel}
						class="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition"
					>
						{cancelText}
					</button>
				{/if}
				<button
					on:click={handleConfirm}
					class="flex-1 px-4 py-2.5 text-sm font-medium text-white rounded-lg transition {colors[type]} hover:opacity-90"
				>
					{confirmText}
				</button>
			</div>
		</div>
	</div>
{/if}
