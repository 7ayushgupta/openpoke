'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

// Get API base URL - must match the Python backend server
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8001';

export default function OAuthCallback() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const run = async () => {
      const code = params.get('code');
      const state = params.get('state');
      if (!code || !state) {
        router.replace('/login');
        return;
      }

      const url = `${API_BASE}/api/v1/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`;
      try {
        const resp = await fetch(url);
        const data = await resp.json();
        if (resp.ok && data?.access_token) {
          localStorage.setItem('openpoke_token', data.access_token);
          router.replace('/');
          return;
        }
      } catch {
        // no-op
      }
      router.replace('/login');
    };
    void run();
  }, [params, router]);

  return null;
}


