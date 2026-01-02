/**
 * Svelte action to portal an element to the document body.
 * This is useful for modals that need to escape parent overflow/transform constraints.
 * 
 * Usage: <div use:portal>...</div>
 */
export function portal(node: HTMLElement, target: HTMLElement = document.body) {
	// Move node to target (body by default)
	target.appendChild(node);

	return {
		destroy() {
			// Clean up by removing the node when component is destroyed
			if (node.parentNode) {
				node.parentNode.removeChild(node);
			}
		}
	};
}
