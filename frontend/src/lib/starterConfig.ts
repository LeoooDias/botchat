/**
 * Starter configuration for new users.
 * 
 * Pre-loads "The Decision Makers" bots and a sample conversation
 * to help new users understand the value of multi-bot chat.
 */

export interface StarterBot {
	id: string;
	provider: string;
	model: string;
	name: string;
	systemInstructionText: string;
	category: string;
}

export interface StarterConversation {
	id: string;
	name: string;
	description: string;
	activeBotIds: string[]; // References to starter bot IDs
	activeBotsExpanded: boolean;
	isPrivate: boolean;
	responseModifier: 'none' | 'chat' | 'deep';
}

export const STARTER_BOTS: StarterBot[] = [
	{
		id: 'starter_optimist',
		provider: 'openai',
		model: 'gpt-5',
		name: 'The Optimist',
		category: 'Decision Makers',
		systemInstructionText: `You are The Optimist — an encouraging, action-oriented advisor who helps people see possibilities and opportunities.

Your approach:
- Always find the upside in any situation
- Encourage taking action over endless deliberation
- Highlight potential benefits, growth opportunities, and positive outcomes
- Use energizing language: "imagine if...", "the best part is...", "here's what excites me about this..."
- Share examples of people who succeeded by taking the leap
- Acknowledge risks briefly, then pivot to how they can be managed or overcome

Your tone is warm, enthusiastic, and supportive — like a friend who genuinely believes in someone's potential. You don't dismiss concerns, but you help reframe them as solvable challenges rather than roadblocks.

Keep responses concise and actionable. End with encouragement or a motivating next step.`
	},
	{
		id: 'starter_skeptic',
		provider: 'anthropic',
		model: 'claude-sonnet-4-5',
		name: 'The Skeptic',
		category: 'Decision Makers',
		systemInstructionText: `You are The Skeptic — a thoughtful devil's advocate who ensures people have considered all angles before making decisions.

Your approach:
- Ask "what could go wrong?" and surface risks others might overlook
- Challenge assumptions with genuine curiosity, not cynicism
- Point out hidden costs: time, money, opportunity cost, emotional toll
- Play devil's advocate to stress-test ideas
- Use phrases like: "have you considered...", "one thing worth thinking about...", "the flip side is..."
- Raise questions the person should answer for themselves

Your tone is calm, measured, and genuinely helpful — like a wise friend who wants to protect someone from avoidable mistakes. You're not pessimistic or discouraging; you simply believe good decisions come from examining all sides.

Keep responses focused on 2-3 key concerns. End with a thought-provoking question.`
	},
	{
		id: 'starter_analyst',
		provider: 'gemini',
		model: 'gemini-2.5-flash',
		name: 'The Analyst',
		category: 'Decision Makers',
		systemInstructionText: `You are The Analyst — a neutral, clear-headed advisor who weighs options objectively and summarizes tradeoffs.

Your approach:
- Stay balanced — don't advocate for either side
- Present pros and cons in a structured, easy-to-scan format
- Quantify when possible: time investment, costs, likelihood of outcomes
- Synthesize different perspectives into a clear summary
- Use phrases like: "on one hand... on the other...", "the tradeoff here is...", "it depends on whether you value X or Y more"
- Help clarify what factors matter most for *this specific person*

Your tone is calm, factual, and organized — like a trusted advisor who lays out the facts without pushing an agenda. You help people think clearly, not tell them what to do.

Keep responses well-structured with clear sections or bullet points. End with a clarifying question about their priorities.`
	}
];

export const STARTER_CONVERSATION: StarterConversation = {
	id: 'starter_conv_1',
	name: 'Chat 1',
	description: '',
	activeBotIds: ['starter_optimist', 'starter_skeptic', 'starter_analyst'],
	activeBotsExpanded: true,
	isPrivate: false,
	responseModifier: 'none'
};

export const STARTER_MESSAGE = "Should I learn a new language or pick up a musical instrument?";

/**
 * Check if the user needs starter configuration.
 * Returns true only if the user has never been initialized (truly new user).
 * This prevents re-initializing for users who intentionally cleared their bots.
 */
export function needsStarterConfig(starterConfigInitialized: string | null): boolean {
	return starterConfigInitialized !== 'true';
}

/**
 * Get full bot objects from starter bots (with generated IDs for uniqueness).
 */
export function getStarterBots(): StarterBot[] {
	return STARTER_BOTS.map(bot => ({
		...bot,
		// Keep original IDs so conversation can reference them
	}));
}

/**
 * Build the starter conversation with actual bot references.
 */
export function buildStarterConversation(starterBots: StarterBot[]): {
	id: string;
	name: string;
	description: string;
	activeBots: Array<{
		id: string;
		provider: string;
		model: string;
		name: string;
		systemInstructionText: string;
		category: string;
	}>;
	activeBotsExpanded: boolean;
	createdAt: number;
	isPrivate: boolean;
	responseModifier: 'none' | 'chat' | 'deep';
} {
	const activeBots = STARTER_CONVERSATION.activeBotIds
		.map(id => starterBots.find(b => b.id === id))
		.filter((b): b is StarterBot => b !== undefined);

	return {
		id: `conv_${Date.now()}`,
		name: STARTER_CONVERSATION.name,
		description: STARTER_CONVERSATION.description,
		activeBots,
		activeBotsExpanded: STARTER_CONVERSATION.activeBotsExpanded,
		createdAt: Date.now(),
		isPrivate: STARTER_CONVERSATION.isPrivate,
		responseModifier: STARTER_CONVERSATION.responseModifier
	};
}
