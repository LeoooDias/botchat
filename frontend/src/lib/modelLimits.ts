/**
 * Model Context Window Limits & Validation
 * 
 * This file contains:
 * 1. Context window sizes (in tokens) for various models
 * 2. Supported models list for validation (models available on platform)
 * 3. Validation utilities to detect deprecated/unavailable models
 * 
 * Populate these values from vendor documentation:
 * - OpenAI: https://platform.openai.com/docs/models
 * - Anthropic: https://docs.anthropic.com/en/docs/about-claude/models
 * - Google Vertex AI: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models
 */

export interface ModelLimit {
	contextWindow: number;  // Total tokens (input + output)
	maxOutput?: number;     // Max output tokens (if different from context)
}

/**
 * Supported models by provider - the single source of truth for available models.
 * Update this when models are added/removed from the platform.
 * These models are available for platform users (not BYOK).
 */
export const SUPPORTED_MODELS: Record<string, string[]> = {
	openai: ['gpt-5.2', 'gpt-5', 'gpt-5-nano', 'gpt-4.1', 'gpt-5-mini'],
	anthropic: ['claude-sonnet-4-5', 'claude-haiku-4-5', 'claude-opus-4-5'],
	gemini: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-lite'],
};

// Context window sizes by provider and model
// Use exact model names as they appear in the model selector
export const MODEL_LIMITS: Record<string, Record<string, ModelLimit>> = {
	openai: {
		'gpt-5.2': { contextWindow: 400000, maxOutput: 128000 },
		'gpt-5': { contextWindow: 400000, maxOutput: 128000 },
		'gpt-5-nano': { contextWindow: 400000, maxOutput: 128000 },
		'gpt-4.1': { contextWindow: 1047576, maxOutput: 32768 },
		'gpt-5-mini': { contextWindow: 400000, maxOutput: 128000 },
	},
	anthropic: {
		'claude-sonnet-4-5': { contextWindow: 200000, maxOutput: 64000 },
		'claude-haiku-4-5': { contextWindow: 200000, maxOutput: 64000 },
		'claude-opus-4-5': { contextWindow: 200000, maxOutput: 64000 },
	},
	gemini: {
		'gemini-2.5-pro': { contextWindow: 1048576, maxOutput: 65536 },
		'gemini-2.5-flash': { contextWindow: 1048576, maxOutput: 65536 },
		'gemini-2.5-flash-lite': { contextWindow: 1048576, maxOutput: 65536 },
	},
};

// Default context window when model is not found (conservative estimate)
export const DEFAULT_CONTEXT_WINDOW = 8192;

/**
 * Get the context window size for a specific provider/model combination.
 * Returns the default if not found.
 */
export function getContextWindow(provider: string, model: string): number {
	const providerLimits = MODEL_LIMITS[provider.toLowerCase()];
	if (providerLimits) {
		// Try exact match first
		if (providerLimits[model]) {
			return providerLimits[model].contextWindow;
		}
		// Try prefix match (e.g., "gpt-4.1-2024-08-06" matches "gpt-4.1")
		for (const [modelKey, limits] of Object.entries(providerLimits)) {
			if (model.startsWith(modelKey)) {
				return limits.contextWindow;
			}
		}
	}
	return DEFAULT_CONTEXT_WINDOW;
}

/**
 * Get the max output tokens for a specific provider/model combination.
 * Returns undefined if not specified (use the model's default or user setting).
 */
export function getMaxOutput(provider: string, model: string): number | undefined {
	const providerLimits = MODEL_LIMITS[provider.toLowerCase()];
	if (providerLimits) {
		if (providerLimits[model]?.maxOutput) {
			return providerLimits[model].maxOutput;
		}
		for (const [modelKey, limits] of Object.entries(providerLimits)) {
			if (model.startsWith(modelKey) && limits.maxOutput) {
				return limits.maxOutput;
			}
		}
	}
	return undefined;
}

/**
 * Check if a provider is supported by the platform.
 */
export function isProviderSupported(provider: string): boolean {
	return provider.toLowerCase() in SUPPORTED_MODELS;
}

/**
 * Check if a specific model is supported/available on the platform.
 * Returns true if the model is in the current supported models list.
 */
export function isModelSupported(provider: string, model: string): boolean {
	const models = SUPPORTED_MODELS[provider.toLowerCase()];
	if (!models) return false;
	return models.includes(model);
}

/**
 * Validate a bot's model configuration.
 * Returns an error message if the model is deprecated/unavailable, or null if valid.
 */
export function validateBotModel(provider: string, model: string): string | null {
	if (!isProviderSupported(provider)) {
		return `Provider "${provider}" is not supported`;
	}
	if (!isModelSupported(provider, model)) {
		const supported = SUPPORTED_MODELS[provider.toLowerCase()] || [];
		return `Model "${model}" is no longer available. Supported models: ${supported.join(', ')}`;
	}
	return null;
}

/**
 * Check if a bot has a valid model configuration.
 */
export function isBotModelValid(bot: { provider: string; model: string }): boolean {
	return validateBotModel(bot.provider, bot.model) === null;
}

/**
 * Get suggested replacement model for a deprecated model.
 * Returns the first available model for the provider, or null if provider not supported.
 */
export function getSuggestedModel(provider: string): string | null {
	const models = SUPPORTED_MODELS[provider.toLowerCase()];
	return models?.[0] || null;
}
