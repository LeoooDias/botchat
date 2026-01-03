<script lang="ts">
	export let files: File[] = [];
	export let hasOversizedFiles = false;

	let isDragging = false;
	let errorMessage = '';

	// Supported file types - keep in sync with backend
	const ALLOWED_EXTENSIONS = [
		// Documents (text extracted for AI)
		'.pdf', '.docx', '.txt', '.md',
		// Images (native support)
		'.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic',
		// Code & Data
		'.json', '.csv', '.xml', '.yaml', '.yml',
		'.py', '.js', '.ts', '.html', '.css'
	];
	const ALLOWED_MIME_TYPES = [
		// Documents
		'application/pdf',
		'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
		'text/plain',
		'text/markdown',
		// Images
		'image/png',
		'image/jpeg',
		'image/gif',
		'image/webp',
		'image/heic',
		// Code & Data
		'application/json',
		'text/csv',
		'application/xml',
		'application/yaml',
		'text/x-python',
		'text/javascript',
		'text/typescript',
		'text/html',
		'text/css'
	];
	const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB limit (Gemini's max for inline PDFs)

	function formatFileSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	function isFileTooLarge(file: File): boolean {
		return file.size > MAX_FILE_SIZE;
	}

	function isFileTypeAllowed(file: File): boolean {
		// Check by extension
		const fileName = file.name.toLowerCase();
		const hasAllowedExtension = ALLOWED_EXTENSIONS.some(ext => fileName.endsWith(ext));
		
		// Check by MIME type (fallback)
		const hasAllowedMimeType = ALLOWED_MIME_TYPES.includes(file.type);
		
		return hasAllowedExtension || hasAllowedMimeType;
	}

	// Reactive: check if any files are oversized
	$: hasOversizedFiles = files.some(isFileTooLarge);

	function processFiles(fileList: File[]): void {
		const validFiles: File[] = [];
		const invalidTypeFiles: string[] = [];
		const oversizedButAllowedFiles: File[] = [];

		for (const file of fileList) {
			if (!isFileTypeAllowed(file)) {
				invalidTypeFiles.push(file.name);
			} else if (isFileTooLarge(file)) {
				// Add oversized files to the list - they'll be shown in red and block sending
				oversizedButAllowedFiles.push(file);
			} else {
				validFiles.push(file);
			}
		}

		const errors: string[] = [];
		if (invalidTypeFiles.length > 0) {
			errors.push(`Unsupported file type${invalidTypeFiles.length > 1 ? 's' : ''}: ${invalidTypeFiles.join(', ')}. Supported: PDF, DOCX, TXT, images (PNG/JPG/GIF/WebP), and code files.`);
		}

		if (errors.length > 0) {
			errorMessage = errors.join(' ');
			// Auto-clear error after 8 seconds
			setTimeout(() => {
				errorMessage = '';
			}, 8000);
		}

		// Add both valid and oversized files (oversized will be displayed in red and block sending)
		const filesToAdd = [...validFiles, ...oversizedButAllowedFiles];
		if (filesToAdd.length > 0) {
			files = [...files, ...filesToAdd];
		}
	}

	function handleFileUpload(e: Event) {
		const input = e.target as HTMLInputElement;
		const newFiles = Array.from(input.files || []);
		processFiles(newFiles);
		// Reset input so same file can be selected again
		input.value = '';
	}

	function handleDragEnter(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		isDragging = true;
	}

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		isDragging = true;
	}

	function handleDragLeave(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		isDragging = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		isDragging = false;

		const droppedFiles = Array.from(e.dataTransfer?.files || []);
		if (droppedFiles.length > 0) {
			processFiles(droppedFiles);
		}
	}

	function removeFile(index: number) {
		files = files.filter((_, i) => i !== index);
	}

	function clearAllFiles() {
		files = [];
	}

	function dismissError() {
		errorMessage = '';
	}
</script>

<div>

	<div class="space-y-2">
		<!-- Drop zone -->
		<div
			class="relative border-2 border-dashed rounded-lg p-3 transition-colors {isDragging 
				? 'border-green-500 bg-green-50 dark:bg-green-900/30' 
				: 'border-gray-300 dark:border-gray-600 hover:border-green-400 dark:hover:border-green-500'}"
			on:dragenter={handleDragEnter}
			on:dragover={handleDragOver}
			on:dragleave={handleDragLeave}
			on:drop={handleDrop}
			role="region"
			aria-label="File drop zone"
		>
			<label for="attachment" class="block cursor-pointer">
				<div class="text-center">
					<div class="flex justify-center mb-1">
						{#if isDragging}
							<svg class="w-7 h-7 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
							</svg>
						{:else}
							<svg class="w-7 h-7 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
							</svg>
						{/if}
					</div>
					<p class="text-xs text-gray-600 dark:text-gray-400">
						{#if isDragging}
							<span class="text-green-600 dark:text-green-400 font-medium">Drop files here</span>
						{:else}
							<span class="hidden md:inline">Drag & drop files or&nbsp;</span><span class="text-green-600 dark:text-green-400 font-medium underline">Tap to browse</span>
						{/if}
					</p>
					<p class="text-xs text-gray-400 dark:text-gray-500 mt-1">PDF, DOCX, TXT, Images, Code • Max 50MB</p>
				</div>
				<input
					id="attachment"
					type="file"
					multiple
						accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.gif,.webp,.heic,.json,.csv,.xml,.yaml,.yml,.py,.js,.ts,.html,.css"
					on:change={handleFileUpload}
					class="sr-only"
				/>
			</label>
		</div>

		<!-- Error message -->
		{#if errorMessage}
			<div class="flex items-start gap-2 bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded p-2">
				<svg class="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
				</svg>
				<p class="text-xs text-red-700 dark:text-red-300 flex-1">{errorMessage}</p>
				<button
					on:click={dismissError}
					class="text-red-500 hover:text-red-700 dark:hover:text-red-300 flex-shrink-0 text-sm leading-none"
					aria-label="Dismiss error"
				>
					✕
				</button>
			</div>
		{/if}

		{#if files.length > 0}
			<!-- Warning if any files are oversized -->
			{#if hasOversizedFiles}
				<div class="flex items-start gap-2 bg-amber-50 dark:bg-amber-900/30 border border-amber-400 dark:border-amber-600 rounded p-2">
					<svg class="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
					</svg>
					<p class="text-xs text-amber-700 dark:text-amber-300 flex-1">
						<strong>Cannot send:</strong> One or more files exceed the 50MB limit. Remove oversized files to continue.
					</p>
				</div>
			{/if}
			<div class="space-y-2">
				{#each files as file, index (index)}
					{@const isTooLarge = isFileTooLarge(file)}
					<div class="flex items-center justify-between rounded p-2 {isTooLarge 
						? 'bg-red-50 dark:bg-red-900/30 border border-red-400 dark:border-red-600' 
						: 'bg-green-50 dark:bg-green-900/30 border border-green-300 dark:border-green-700'}">
						<div class="flex-1 min-w-0">
							<p class="text-xs font-semibold truncate {isTooLarge ? 'text-red-900 dark:text-red-200' : 'text-green-900 dark:text-green-200'}">{file.name}</p>
							<p class="text-xs {isTooLarge ? 'text-red-600 dark:text-red-400 font-medium' : 'text-green-700 dark:text-green-400'}">
								{formatFileSize(file.size)}{#if isTooLarge} — exceeds 50MB limit{/if}
							</p>
						</div>
						<button
							on:click={() => removeFile(index)}
							class="px-2 py-1 text-xs bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900 transition ml-2 flex-shrink-0"
						>
							Remove
						</button>
					</div>
				{/each}
				<button
					on:click={clearAllFiles}
					class="w-full px-2 py-1 text-xs bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900 transition"
				>
					Clear All
				</button>
			</div>
		{:else}
			<p class="text-xs text-gray-500 dark:text-gray-400 italic">Sent with every prompt</p>
		{/if}
	</div>
</div>
