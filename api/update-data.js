// Vercel Serverless Function - Trigger data update via GitHub Actions
// This function is called by Vercel Cron Jobs every 15 minutes
// It triggers the GitHub Actions workflow to update dashboard data

export default async function handler(request, response) {
  // Verify this is a Vercel Cron request (security check)
  const authHeader = request.headers.authorization;
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    console.log('[CRON] Unauthorized request');
    return response.status(401).json({ error: 'Unauthorized' });
  }

  const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
  const GITHUB_OWNER = 'gabrielfeliperibeiro';
  const GITHUB_REPO = 'bees_dash';
  const WORKFLOW_ID = 'update-dashboard.yml';

  if (!GITHUB_TOKEN) {
    console.error('[CRON] Missing GITHUB_TOKEN environment variable');
    return response.status(500).json({
      error: 'Server configuration error',
      message: 'GITHUB_TOKEN not configured'
    });
  }

  try {
    console.log('[CRON] Triggering data update workflow...');

    // Trigger the GitHub Actions workflow
    const workflowUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`;

    const workflowResponse = await fetch(workflowUrl, {
      method: 'POST',
      headers: {
        'Accept': 'application/vnd.github+json',
        'Authorization': `Bearer ${GITHUB_TOKEN}`,
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'BEES-Dashboard-Cron',
      },
      body: JSON.stringify({
        ref: 'main', // Branch to run workflow on
      }),
    });

    if (!workflowResponse.ok) {
      const errorText = await workflowResponse.text();
      console.error('[CRON] Workflow trigger failed:', workflowResponse.status, errorText);
      throw new Error(`GitHub API error: ${workflowResponse.status} - ${errorText}`);
    }

    console.log('[CRON] ✅ Workflow triggered successfully');

    return response.status(200).json({
      success: true,
      message: 'Data update workflow triggered',
      timestamp: new Date().toISOString(),
      workflow: WORKFLOW_ID,
    });

  } catch (error) {
    console.error('[CRON] Error triggering workflow:', error);

    return response.status(500).json({
      success: false,
      error: 'Failed to trigger data update',
      message: error.message,
      timestamp: new Date().toISOString(),
    });
  }
}
