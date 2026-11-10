// Login for /admin, step 2: GitHub sends the editor back here. We swap the one-time code for a token
// and hand it to the admin window, using the message format Decap CMS expects.
export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  const saved = ((request.headers.get('Cookie') || '').match(/(?:^|;\s*)oauth_state=([^;]+)/) || [])[1];

  let status = 'error';
  let content = { message: 'Inloggen is mislukt. Sluit dit venster en probeer het opnieuw.' };
  if (code && state && saved && state === saved) {
    try {
      const response = await fetch('https://github.com/login/oauth/access_token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'User-Agent': 'dandelion-circularity-admin' },
        body: JSON.stringify({
          client_id: env.GITHUB_CLIENT_ID,
          client_secret: env.GITHUB_CLIENT_SECRET,
          code: code,
          redirect_uri: url.origin + '/api/callback',
        }),
      });
      const data = await response.json();
      if (data.access_token) {
        status = 'success';
        content = { token: data.access_token, provider: 'github' };
      }
    } catch (e) {
      // keep the error message above
    }
  }

  const message = 'authorization:github:' + status + ':' + JSON.stringify(content);
  const js = (value) => JSON.stringify(value).replace(/</g, '\\u003c');
  const html = '<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>Inloggen</title></head><body>'
    + '<p>' + (status === 'success' ? 'Een moment…' : content.message) + '</p><script>'
    + '(function () {'
    + '  var origin = ' + js(url.origin) + ';'
    + '  if (!window.opener) return;'
    + '  function receive(e) {'
    + '    if (e.origin !== origin || e.data !== "authorizing:github") return;'
    + '    window.removeEventListener("message", receive);'
    + '    window.opener.postMessage(' + js(message) + ', origin);'
    + '  }'
    + '  window.addEventListener("message", receive);'
    + '  window.opener.postMessage("authorizing:github", origin);'
    + '})();'
    + '</script></body></html>';

  return new Response(html, {
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'Set-Cookie': 'oauth_state=; Path=/api; HttpOnly; Secure; SameSite=Lax; Max-Age=0',
    },
  });
}
