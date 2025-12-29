/**
 * Model Context Window Limits
 * 
 * This file contains the context window sizes (in tokens) for various models.
 * The context window is the maximum total tokens (input + output) a model can handle.
 * 
 * Populate these values from vendor documentation:
 * - OpenAI: https://platform.openai.com/docs/models
 * - Anthropic: https://docs.anthropic.com/en/docs/about-claude/models
 * - Google: https://ai.google.dev/gemini-api/docs/models/gemini
 */

export interface ModelLimit {
	contextWindow: number;  // Total tokens (input + output)
	maxOutput?: number;     // Max output tokens (if different from context)
}

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
		'gemini-3-pro-preview': { contextWindow: 1048576, maxOutput: 65536 },
		'gemini-3-flash-preview': { contextWindow: 1048576, maxOutput: 65536 },
		'gemini-2.5-flash': { contextWindow: 1048576, maxOutput: 65536 },
		'gemini-2.5-flash-lite': { contextWindow: 1048576, maxOutput: 65536 },
		'gemini-2.5-pro': { contextWindow: 1048576, maxOutput: 65536 },
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
