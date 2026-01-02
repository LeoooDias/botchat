<script lang="ts">
	import { onMount } from 'svelte';

	let isDark = false;

	onMount(() => {
		// Check for saved theme preference or system preference
		const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
		if (savedTheme) {
			isDark = savedTheme === 'dark';
		} else {
			isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		}
		document.documentElement.classList.toggle('dark', isDark);
	});
</script>

<svelte:head>
	<title>Privacy Statement | botchat</title>
</svelte:head>

<div class="min-h-screen bg-white dark:bg-gray-900 transition-colors">
	<!-- Header -->
	<div class="bg-gradient-to-r from-blue-600 to-blue-700 dark:from-blue-800 dark:to-blue-900 text-white px-4 py-2 shadow">
		<div class="flex items-center justify-between">
			<a href="/" class="flex items-end gap-3 hover:opacity-90 transition-opacity">
				<h1 class="text-4xl font-bold leading-none">botchat</h1>
				<p class="text-blue-100 text-xs leading-tight">many minds<br/>no memory</p>
			</a>
			<div class="flex items-center gap-4">
				<a href="/" class="text-sm hover:text-blue-100 transition-colors">← Back</a>
			</div>
		</div>
	</div>

	<!-- Content -->
	<div class="max-w-3xl mx-auto px-4 py-8">
		<article class="prose prose-gray dark:prose-invert max-w-none">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">Privacy Statement</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400 mb-8">Last updated: January 2, 2026</p>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">1. Introduction</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					botchat ("we," "our," or "the Service") is designed with privacy as a core principle. This Privacy Statement explains what data we collect, how we handle it, and the technical measures we implement to protect your privacy.
				</p>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					<strong>Our commitment:</strong> We collect the minimum data necessary to operate the Service, we never sell or share your personal data with third parties for marketing purposes, and we implement extensive technical measures to protect your information.
				</p>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">2. Data We Collect</h2>
				
				<h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4 mb-2">2.1 Account Data</h3>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					When you create an account, we store:
				</p>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li><strong>OAuth provider identifier:</strong> A unique ID from your sign-in provider (not your password)</li>
					<li><strong>Email address:</strong> If provided by your OAuth provider, used for account identification</li>
					<li><strong>Account creation date:</strong> When you first signed up</li>
					<li><strong>Subscription status:</strong> Your current plan and expiration date (if applicable)</li>
					<li><strong>Message count:</strong> Number of messages sent during the current billing period (platform keys only)</li>
				</ul>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					<strong>We do NOT store:</strong> Your name, profile picture, or any data beyond what is listed above.
				</p>

				<h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4 mb-2">2.2 Chat Data</h3>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					<strong>We do NOT store your conversations.</strong> Your chat history, prompts, bot responses, and attachments are stored exclusively in your browser's local storage. This data never touches our servers. If you clear your browser data or switch devices, your conversations are gone—this is by design.
				</p>

				<h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4 mb-2">2.3 API Keys (BYOK)</h3>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					If you use your own API keys (Bring Your Own Key):
				</p>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li>Keys are encrypted with AES-256 in your browser before storage</li>
					<li>Encrypted keys are stored in your browser's local storage</li>
					<li>Keys are decrypted client-side and sent directly to AI providers</li>
					<li>Your API keys are never transmitted to or stored on botchat servers</li>
				</ul>

				<h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4 mb-2">2.4 Bot Configurations</h3>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					Your saved bots, system instructions, and preferences are stored locally in your browser. We do not have access to this data.
				</p>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">3. Data We Do NOT Collect</h2>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li>Chat messages or conversation history</li>
					<li>File attachments or their contents</li>
					<li>Bot system instructions or personas</li>
					<li>Your name (unless included in your email)</li>
					<li>Browsing history or activity outside the Service</li>
					<li>Location data</li>
					<li>Device identifiers or fingerprints</li>
				</ul>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">4. Third-Party AI Providers</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					When you send a message, it is transmitted to the AI provider (OpenAI, Anthropic, or Google) for processing. botchat acts as a relay—we do not store or inspect message content.
				</p>

				<h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4 mb-2">4.1 Training Opt-Out Guarantees</h3>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					We ensure your data is NOT used for AI model training by implementing the following:
				</p>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li><strong>OpenAI:</strong> <code>store=False</code> parameter set on every request; <code>X-OpenAI-No-Store</code> header sent</li>
					<li><strong>Anthropic:</strong> API usage excluded from training by default per Anthropic policy</li>
					<li><strong>Google Gemini:</strong> Vertex AI backend (enterprise-grade) used for platform keys</li>
				</ul>

				<h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4 mb-2">4.2 Provider Data Retention</h3>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					AI providers may temporarily retain data for trust & safety purposes (abuse monitoring, legal compliance):
				</p>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li><strong>Anthropic:</strong> Up to 30 days</li>
					<li><strong>OpenAI:</strong> Variable retention window based on account tier</li>
					<li><strong>Google:</strong> Up to 30 days</li>
				</ul>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					This retention is for safety purposes only—not training. After the retention window, data is deleted.
				</p>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">5. Technical Privacy Protections</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					We implement extensive technical measures to protect your privacy:
				</p>

				<h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4 mb-2">5.1 Image & Attachment Handling</h3>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li><strong>EXIF metadata stripping:</strong> GPS coordinates, device identifiers, timestamps, and camera settings are removed from images before transmission</li>
					<li><strong>In-memory processing:</strong> Attachments stream through memory buffers (BytesIO)—files never touch disk on our servers</li>
					<li><strong>No attachment storage:</strong> Files are transmitted directly to AI providers and immediately discarded</li>
				</ul>

				<h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4 mb-2">5.2 Logging Controls</h3>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li><strong>Minimal logging:</strong> Production log level is WARNING—DEBUG requires explicit opt-in</li>
					<li><strong>No content logging:</strong> Prompts, responses, and message content are never logged</li>
					<li><strong>Access logs suppressed:</strong> URL paths and query parameters are not logged</li>
					<li><strong>Metadata stripped:</strong> Filenames and sensitive metadata excluded from logs by default</li>
					<li><strong>Error logging sanitized:</strong> Exception handling extracts only error codes—never request content</li>
				</ul>

				<h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4 mb-2">5.3 User Identity Protection</h3>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li><strong>PII validation:</strong> If raw PII (emails, phone numbers, SSNs) is accidentally passed as a user identifier, it's detected and rejected</li>
					<li><strong>Hashed identifiers:</strong> User IDs sent to AI providers are opaque identifiers, never raw personal information</li>
					<li><strong>Provider-based accounts:</strong> Accounts keyed by stable OAuth provider ID, not email addresses</li>
				</ul>

				<h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4 mb-2">5.4 SDK Telemetry</h3>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li><strong>OpenAI SDK headers minimized:</strong> <code>X-Stainless-*</code> telemetry headers set to "private"</li>
					<li><strong>Prompt caching disabled:</strong> We never set <code>prompt_cache_key</code> or <code>prompt_cache_retention</code></li>
				</ul>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">6. Data Security</h2>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li><strong>Encryption in transit:</strong> All communications use TLS 1.2+</li>
					<li><strong>API key encryption:</strong> BYOK keys encrypted with AES-256 client-side; server-side storage (if used) uses PBKDF2 with 480,000 iterations</li>
					<li><strong>JWT authentication:</strong> Stateless, short-lived tokens with no server-side session storage</li>
					<li><strong>Memory cleanup:</strong> Attachment data explicitly dereferenced after processing</li>
				</ul>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">7. Payment Processing</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					Payments are processed by Stripe. We do not store credit card numbers, CVVs, or full payment details. Stripe's privacy policy governs payment data: <a href="https://stripe.com/privacy" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">stripe.com/privacy</a>
				</p>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">8. Cookies and Tracking</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					botchat uses only essential cookies for authentication (JWT tokens). We do not use:
				</p>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li>Analytics or tracking cookies</li>
					<li>Advertising cookies</li>
					<li>Third-party tracking pixels</li>
					<li>Social media tracking</li>
				</ul>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">9. Data Retention</h2>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li><strong>Account data:</strong> Retained while your account is active; deleted upon account deletion request</li>
					<li><strong>Chat data:</strong> Not retained by us—stored only in your browser</li>
					<li><strong>Message counts:</strong> Reset monthly for billing purposes</li>
					<li><strong>Logs:</strong> Server logs retained for up to 30 days for operational purposes, containing no message content</li>
				</ul>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">10. Your Rights</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					You have the right to:
				</p>
				<ul class="list-disc pl-6 text-gray-600 dark:text-gray-400 mb-4 space-y-2">
					<li><strong>Access:</strong> Request a copy of the account data we store about you</li>
					<li><strong>Deletion:</strong> Request deletion of your account and associated data</li>
					<li><strong>Portability:</strong> Export your locally-stored chat data from your browser</li>
					<li><strong>Correction:</strong> Update your account information</li>
				</ul>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					To exercise these rights, contact: <a href="mailto:leo@botchat.ca" class="text-blue-600 dark:text-blue-400 hover:underline">leo@botchat.ca</a>
				</p>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">11. Children's Privacy</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					botchat is not intended for use by individuals under 13 years of age. We do not knowingly collect personal information from children.
				</p>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">12. International Data Transfers</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					The Service is hosted in North America. By using botchat, you consent to your data being processed in Canada and the United States. AI provider data processing locations are governed by their respective privacy policies.
				</p>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">13. Open Source Transparency</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					botchat is open source. You can audit our privacy practices by reviewing the code: <a href="https://github.com/LeoooDias/botchat" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">github.com/LeoooDias/botchat</a>
				</p>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">14. Changes to This Statement</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					We may update this Privacy Statement periodically. Material changes will be communicated through the Service. Continued use after changes constitutes acceptance.
				</p>
			</section>

			<section class="mb-8">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">15. Contact</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-4">
					For privacy-related questions or concerns, contact: <a href="mailto:leo@botchat.ca" class="text-blue-600 dark:text-blue-400 hover:underline">leo@botchat.ca</a>
				</p>
			</section>

			<section class="mb-8 bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Summary</h2>
				<p class="text-gray-600 dark:text-gray-400 text-sm">
					<strong>What we store:</strong> Minimal account data (OAuth ID, email, subscription status, message count).<br/>
					<strong>What we don't store:</strong> Your chats, attachments, bot configs, or API keys.<br/>
					<strong>Training opt-out:</strong> Your data is never used for AI model training.<br/>
					<strong>Transparency:</strong> Our code is open source—audit it yourself.
				</p>
			</section>
		</article>
	</div>
</div>
