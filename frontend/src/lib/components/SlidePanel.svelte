<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fly, fade } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';

	export let open = false;
	export let side: 'left' | 'right' | 'bottom' = 'left';
	export let title = '';
	export let showHeader = true;

	const dispatch = createEventDispatcher<{ close: void }>();

	function handleClose() {
		dispatch('close');
	}

	function handleBackdropClick() {
		handleClose();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			handleClose();
		}
	}

	// Swipe to close logic
	let startX = 0;
	let startY = 0;
	let currentX = 0;
	let currentY = 0;
	let isDragging = false;
	let hasMoved = false; // Track if user has actually moved (not just tapped)
	let panelElement: HTMLDivElement;

	const SWIPE_THRESHOLD = 100; // pixels to trigger close
	const VELOCITY_THRESHOLD = 0.5; // pixels/ms
	const MOVE_THRESHOLD = 10; // pixels before we consider it a swipe (not a tap)
	let startTime = 0;

	function handleTouchStart(e: TouchEvent) {
		if (!open) return;
		// Don't capture touches on interactive elements
		const target = e.target as HTMLElement;
		if (target.closest('button, a, input, select, textarea, [role="button"]')) {
			return;
		}
		startX = e.touches[0].clientX;
		startY = e.touches[0].clientY;
		startTime = Date.now();
		isDragging = true;
		hasMoved = false;
	}

	function handleTouchMove(e: TouchEvent) {
		if (!isDragging || !open) return;

		currentX = e.touches[0].clientX;
		currentY = e.touches[0].clientY;

		const deltaX = currentX - startX;
		const deltaY = currentY - startY;

		// Only start visual movement after passing threshold (prevents jitter on taps)
		if (!hasMoved && Math.abs(deltaX) < MOVE_THRESHOLD && Math.abs(deltaY) < MOVE_THRESHOLD) {
			return;
		}
		hasMoved = true;

		// Determine if horizontal swipe
		if (Math.abs(deltaX) > Math.abs(deltaY)) {
			// Left panel: swipe left to close
			if (side === 'left' && deltaX < 0) {
				const transform = Math.max(deltaX, -window.innerWidth);
				panelElement.style.transform = `translateX(${transform}px)`;
				e.preventDefault();
			}
			// Right panel: swipe right to close
			else if (side === 'right' && deltaX > 0) {
				const transform = Math.min(deltaX, window.innerWidth);
				panelElement.style.transform = `translateX(${transform}px)`;
				e.preventDefault();
			}
		}

		// Bottom panel: swipe down to close
		if (side === 'bottom' && deltaY > 0) {
			const transform = Math.min(deltaY, window.innerHeight);
			panelElement.style.transform = `translateY(${transform}px)`;
			e.preventDefault();
		}
	}

	function handleTouchEnd() {
		if (!isDragging || !open) return;

		const deltaX = currentX - startX;
		const deltaY = currentY - startY;
		const elapsed = Date.now() - startTime;
		const velocityX = Math.abs(deltaX) / elapsed;
		const velocityY = Math.abs(deltaY) / elapsed;

		let shouldClose = false;

		// Only close if user actually moved (swiped), not just tapped
		if (hasMoved) {
			if (side === 'left') {
				shouldClose = deltaX < -SWIPE_THRESHOLD || (deltaX < 0 && velocityX > VELOCITY_THRESHOLD);
			} else if (side === 'right') {
				shouldClose = deltaX > SWIPE_THRESHOLD || (deltaX > 0 && velocityX > VELOCITY_THRESHOLD);
			} else if (side === 'bottom') {
				shouldClose = deltaY > SWIPE_THRESHOLD || (deltaY > 0 && velocityY > VELOCITY_THRESHOLD);
			}
		}

		// Reset transform
		if (panelElement) {
			panelElement.style.transform = '';
		}

		if (shouldClose) {
			handleClose();
		}

		isDragging = false;
		hasMoved = false;
		startX = 0;
		startY = 0;
		currentX = 0;
		currentY = 0;
	}

	// Transition configs
	$: flyParams = {
		left: { x: -320, duration: 300, easing: cubicOut },
		right: { x: 320, duration: 300, easing: cubicOut },
		bottom: { y: 400, duration: 300, easing: cubicOut }
	}[side];

	$: panelClasses = {
		left: 'left-0 top-0 bottom-0 w-[85vw] max-w-sm safe-left',
		right: 'right-0 top-0 bottom-0 w-[85vw] max-w-sm safe-right',
		bottom: 'left-0 right-0 bottom-0 max-h-[85vh] rounded-t-2xl'
	}[side];
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 bg-black/50 backdrop-blur-mobile md:hidden"
		on:click={handleBackdropClick}
		on:keydown={(e) => e.key === 'Enter' && handleBackdropClick()}
		role="button"
		tabindex="-1"
		aria-label="Close panel"
		transition:fade={{ duration: 200 }}
	></div>

	<!-- Panel -->
	<div
		bind:this={panelElement}
		class="fixed z-50 bg-white dark:bg-gray-800 shadow-2xl flex flex-col overflow-hidden md:hidden {panelClasses}"
		transition:fly={flyParams}
		on:touchstart={handleTouchStart}
		on:touchmove={handleTouchMove}
		on:touchend={handleTouchEnd}
		role="dialog"
		aria-modal="true"
		aria-label={title}
	>
		<!-- Drag handle for bottom sheet -->
		{#if side === 'bottom'}
			<div class="flex justify-center py-2 cursor-grab active:cursor-grabbing">
				<div class="w-12 h-1.5 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
			</div>
		{/if}

		<!-- Header -->
		{#if showHeader}
			<div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex-shrink-0 safe-top">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
				<button
					on:click={handleClose}
					class="touch-target flex items-center justify-center text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition mobile-tap-highlight"
					aria-label="Close"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
		{/if}

		<!-- Content -->
		<div class="flex-1 overflow-y-auto mobile-scroll mobile-hide-scrollbar {side === 'bottom' ? 'pb-safe' : ''}">
			<slot />
		</div>
	</div>
{/if}
