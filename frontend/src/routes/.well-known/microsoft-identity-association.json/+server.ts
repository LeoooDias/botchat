import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';
import type { RequestHandler } from './$types';

/**
 * Serve Microsoft identity association JSON for domain verification.
 * The applicationId is pulled from environment variable to support
 * different values for dev vs prod environments.
 */
export const GET: RequestHandler = async () => {
	const applicationId = env.PUBLIC_MICROSOFT_APP_ID;
	
	if (!applicationId) {
		return json(
			{ error: 'MICROSOFT_APP_ID not configured' },
			{ status: 500 }
		);
	}
	
	return json({
		associatedApplications: [
			{
				applicationId
			}
		]
	});
};
