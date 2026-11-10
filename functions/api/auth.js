// Login for /admin, step 1: send the editor to GitHub to approve access.
// Runs on Cloudflare Pages. Needs the variables GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET (see SETUP.md).
export async function onRequestGet({ request, env }) {
  if (!env.GITHUB_CLIENT_ID) {
    return new Response('GITHUB_CLIENT_ID is not set in the Cloudflare Pages settings.', { status: 500 });
  }
  const origin = new URL(request.url).origin;
  const state = crypto.randomUUID();
  const github = new URL('https://github.com/login/oauth/authorize');
  github.searchParams.set('client_id', env.GITHUB_CLIENT_ID);
  github.searchParams.set('redirect_uri', origin + '/api/callback');
  github.searchParams.set('scope', 'repo,user');
  github.searchParams.set('state', state);
  return new Response(null, {
    status: 302,
    headers: {
      Location: github.toString(),
      // Only for editors logging in: protects the login against forged requests. Expires after 10 minutes.
      'Set-Cookie': 'oauth_state=' + state + '; Path=/api; HttpOnly; Secure; SameSite=Lax; Max-Age=600',
      'Cache-Control': 'no-store',
    },
  });
}
