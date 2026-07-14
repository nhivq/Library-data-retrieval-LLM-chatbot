import { useEffect, useState } from 'react';
import { Auth, routeTo } from '../api/client.js';

export default function OAuthSuccessPage() {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const access = params.get('access');
    const refresh = params.get('refresh');

    if (access && refresh) {
      Auth.saveTokens({
        access_token: access,
        refresh_token: refresh,
      });
      routeTo('/chat');
    } else {
      setFailed(true);
    }
  }, []);

  return <p style={{ padding: 24 }}>{failed ? 'OAuth login failed' : 'Logging in...'}</p>;
}
