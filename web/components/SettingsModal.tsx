"use client";
import { useCallback, useEffect, useMemo, useState } from 'react';

export type Settings = {
  timezone: string;
};

export function useSettings() {
  const [settings, setSettings] = useState<Settings>({ timezone: '' });

  useEffect(() => {
    try {
      const timezone = localStorage.getItem('user_timezone') || '';
      setSettings({ timezone });
    } catch {}
  }, []);

  const persist = useCallback((s: Settings) => {
    setSettings(s);
    try {
      localStorage.setItem('user_timezone', s.timezone);
    } catch {}
  }, []);

  return { settings, setSettings: persist } as const;
}

function coerceEmailFrom(value: unknown): string | null {
  if (typeof value === 'string' && value.includes('@')) {
    return value;
  }
  if (value && typeof value === 'object') {
    const candidate =
      (value as any).emailAddress ??
      (value as any).email ??
      (value as any).value ??
      (value as any).address;
    if (typeof candidate === 'string' && candidate.includes('@')) {
      return candidate;
    }
  }
  return null;
}

function deriveEmailFromPayload(payload: any): string {
  if (!payload) return '';
  const profileSlice = payload?.profile;
  const candidateObjects: any[] = [];

  if (profileSlice && typeof profileSlice === 'object') {
    candidateObjects.push(profileSlice);
    if ((profileSlice as any).response_data && typeof (profileSlice as any).response_data === 'object') {
      candidateObjects.push((profileSlice as any).response_data);
    }
    if (Array.isArray((profileSlice as any).items)) {
      for (const entry of (profileSlice as any).items as any[]) {
        if (entry && typeof entry === 'object') {
          if (typeof entry.data === 'object') candidateObjects.push(entry.data);
          if (typeof entry.response_data === 'object') candidateObjects.push(entry.response_data);
          if (typeof entry.profile === 'object') candidateObjects.push(entry.profile);
        }
      }
    }
  }

  const directCandidates = [payload?.email];

  for (const obj of candidateObjects) {
    if (!obj || typeof obj !== 'object') continue;
    directCandidates.push(
      obj?.email,
      obj?.email_address,
      obj?.emailAddress,
      obj?.profile?.email,
      obj?.profile?.emailAddress,
      obj?.profile?.email_address,
      obj?.user?.email,
      obj?.user?.emailAddress,
      obj?.user?.email_address,
      obj?.data?.email,
      obj?.data?.emailAddress,
      obj?.data?.email_address,
    );
    const emailAddresses = (obj as any).emailAddresses;
    if (Array.isArray(emailAddresses)) {
      for (const entry of emailAddresses) {
        const email = coerceEmailFrom(entry) ?? coerceEmailFrom((entry as any)?.value);
        if (email) return email;
      }
    }
  }

  for (const candidate of directCandidates) {
    const email = coerceEmailFrom(candidate);
    if (email) return email;
  }

  return '';
}

export default function SettingsModal({
  open,
  onClose,
  settings,
  onSave,
}: {
  open: boolean;
  onClose: () => void;
  settings: Settings;
  onSave: (s: Settings) => void;
}) {
  const [timezone, setTimezone] = useState(settings.timezone);
  const [connectingGmail, setConnectingGmail] = useState(false);
  const [isRefreshingGmail, setIsRefreshingGmail] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [gmailStatusMessage, setGmailStatusMessage] = useState('');
  const [gmailConnected, setGmailConnected] = useState(false);
  const [gmailEmail, setGmailEmail] = useState('');
  const [gmailConnId, setGmailConnId] = useState('');
  const [gmailProfile, setGmailProfile] = useState<Record<string, unknown> | null>(null);
  
  // MCP state
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [mcpTools, setMcpTools] = useState<any[]>([]);
  const [loadingMcp, setLoadingMcp] = useState(false);
  const [newServerName, setNewServerName] = useState('');
  const [newServerUrl, setNewServerUrl] = useState('');
  const [newServerAuthType, setNewServerAuthType] = useState('none');
  const [newServerApiKey, setNewServerApiKey] = useState('');

  const readStoredUserId = useCallback(() => {
    if (typeof window === 'undefined') return '';
    try {
      return localStorage.getItem('openpoke_user_id') || '';
    } catch {
      return '';
    }
  }, []);

  const ensureUserId = useCallback(() => {
    if (typeof window === 'undefined') {
      return `web-${Math.random().toString(36).slice(2)}`;
    }
    try {
      const existing = localStorage.getItem('openpoke_user_id');
      if (existing) return existing;
      const cryptoObj = (globalThis as { crypto?: Crypto }).crypto;
      const randomPart =
        cryptoObj && typeof cryptoObj.randomUUID === 'function'
          ? cryptoObj.randomUUID().replace(/-/g, '')
          : Math.random().toString(36).slice(2);
      const generated = `web-${randomPart}`;
      localStorage.setItem('openpoke_user_id', generated);
      return generated;
    } catch {
      return `web-${Math.random().toString(36).slice(2)}`;
    }
  }, []);

  const readStoredConnectionRequestId = useCallback(() => {
    if (gmailConnId) return gmailConnId;
    if (typeof window === 'undefined') return '';
    try {
      return localStorage.getItem('gmail_connection_request_id') || '';
    } catch {
      return '';
    }
  }, [gmailConnId]);

  useEffect(() => {
    try {
      const savedConnected = localStorage.getItem('gmail_connected') === 'true';
      const savedConnId = localStorage.getItem('gmail_connection_request_id') || '';
      const savedEmail = localStorage.getItem('gmail_email') || '';
      setGmailConnected(savedConnected);
      setGmailConnId(savedConnId);
      setGmailEmail(savedEmail);
      if (savedConnected && savedEmail) {
        setGmailStatusMessage(`Connected as ${savedEmail}`);
      }
    } catch {}
  }, []);

  const gmailProfileDetails = useMemo(() => {
    if (!gmailProfile) return [] as { label: string; value: string }[];
    const details: { label: string; value: string }[] = [];
    const messagesTotal = (gmailProfile as any)?.messagesTotal;
    if (typeof messagesTotal === 'number') {
      details.push({ label: 'Messages', value: messagesTotal.toLocaleString() });
    }
    const threadsTotal = (gmailProfile as any)?.threadsTotal;
    if (typeof threadsTotal === 'number') {
      details.push({ label: 'Threads', value: threadsTotal.toLocaleString() });
    }
    const historyId = (gmailProfile as any)?.historyId ?? (gmailProfile as any)?.historyID;
    if (historyId !== undefined && historyId !== null && historyId !== '') {
      details.push({ label: 'History ID', value: String(historyId) });
    }
    return details;
  }, [gmailProfile]);

  // MCP functions
  const loadMcpServers = useCallback(async () => {
    try {
      setLoadingMcp(true);
      const resp = await fetch('/api/mcp/servers');
      if (resp.ok) {
        const data = await resp.json();
        setMcpServers(data.servers || []);
      }
    } catch (err) {
      console.error('Failed to load MCP servers:', err);
    } finally {
      setLoadingMcp(false);
    }
  }, []);

  const loadMcpTools = useCallback(async () => {
    try {
      const resp = await fetch('/api/mcp/tools');
      if (resp.ok) {
        const data = await resp.json();
        setMcpTools(data.tools || []);
      }
    } catch (err) {
      console.error('Failed to load MCP tools:', err);
    }
  }, []);

  const addMcpServer = useCallback(async () => {
    if (!newServerName || !newServerUrl) return;
    
    try {
      setLoadingMcp(true);
      const payload: any = {
        server_name: newServerName,
        url: newServerUrl,
        auth_type: newServerAuthType === 'none' ? null : newServerAuthType,
      };
      
      if (newServerAuthType === 'api_key' && newServerApiKey) {
        payload.auth_config = { api_key: newServerApiKey };
      }
      
      const resp = await fetch('/api/mcp/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      
      if (resp.ok) {
        setNewServerName('');
        setNewServerUrl('');
        setNewServerAuthType('none');
        setNewServerApiKey('');
        await loadMcpServers();
        await loadMcpTools();
      }
    } catch (err) {
      console.error('Failed to add MCP server:', err);
    } finally {
      setLoadingMcp(false);
    }
  }, [newServerName, newServerUrl, newServerAuthType, newServerApiKey, loadMcpServers, loadMcpTools]);

  const removeMcpServer = useCallback(async (serverName: string) => {
    try {
      setLoadingMcp(true);
      const resp = await fetch(`/api/mcp/servers/${encodeURIComponent(serverName)}`, {
        method: 'DELETE',
      });
      
      if (resp.ok) {
        await loadMcpServers();
        await loadMcpTools();
      }
    } catch (err) {
      console.error('Failed to remove MCP server:', err);
    } finally {
      setLoadingMcp(false);
    }
  }, [loadMcpServers, loadMcpTools]);

  useEffect(() => {
    if (open) {
      loadMcpServers();
      loadMcpTools();
    }
  }, [open, loadMcpServers, loadMcpTools]);

  const handleConnectGmail = useCallback(async () => {
    try {
      setConnectingGmail(true);
      setGmailStatusMessage('');
      const userId = ensureUserId();
      const resp = await fetch('/api/gmail/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || !data?.ok) {
        const msg = data?.error || `Failed (${resp.status})`;
        setGmailStatusMessage(msg);
        return;
      }
      const url = data?.redirect_url;
      const connId = data?.connection_request_id || '';
      if (connId) {
        setGmailConnId(connId);
        try {
          localStorage.setItem('gmail_connection_request_id', connId);
        } catch {}
      }
      setGmailConnected(false);
      setGmailEmail('');
      setGmailProfile(null);
      if (url) {
        window.open(url, '_blank', 'noopener');
        setGmailStatusMessage('Gmail authorization opened in a new tab. Complete it, then press “Refresh status”.');
      } else {
        setGmailStatusMessage('Connection initiated. Refresh status once authorization completes.');
      }
    } catch (e: any) {
      setGmailStatusMessage(e?.message || 'Failed to connect Gmail');
    } finally {
      setConnectingGmail(false);
    }
  }, [ensureUserId]);

  const refreshGmailStatus = useCallback(async () => {
    const userId = readStoredUserId();
    const connectionRequestId = readStoredConnectionRequestId();
    if (!userId && !connectionRequestId) {
      setGmailConnected(false);
      setGmailProfile(null);
      setGmailEmail('');
      setGmailStatusMessage('Connect Gmail to get started.');
      return;
    }

    try {
      setIsRefreshingGmail(true);
      setGmailStatusMessage('Refreshing Gmail status…');
      const resp = await fetch('/api/gmail/status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, connectionRequestId }),
      });
      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || !data?.ok) {
        const message = data?.error || `Failed (${resp.status})`;
        setGmailConnected(false);
        setGmailProfile(null);
        setGmailEmail('');
        setGmailStatusMessage(message);
        return;
      }

      if (!gmailConnId && connectionRequestId) {
        setGmailConnId(connectionRequestId);
      }

      const profileData = data?.profile && typeof data.profile === 'object' ? (data.profile as Record<string, unknown>) : null;
      setGmailProfile(profileData);

      const derivedEmail = deriveEmailFromPayload({ email: data?.email, profile: profileData });
      const email = derivedEmail || (typeof data?.email === 'string' ? data.email : '');
      const connected = Boolean(data?.connected);

      setGmailConnected(connected);
      setGmailEmail(email);

      if (connected) {
        const source = typeof data?.profile_source === 'string' ? data.profile_source : '';
        const sourceNote = source === 'fetched' ? 'Verified moments ago.' : source === 'cache' ? 'Loaded from cache.' : '';
        const message = email ? `Connected as ${email}` : 'Gmail connected.';
        setGmailStatusMessage(sourceNote ? `${message} ${sourceNote}` : message);
        try {
          localStorage.setItem('gmail_connected', 'true');
          if (email) localStorage.setItem('gmail_email', email);
          if (typeof data?.user_id === 'string' && data.user_id) {
            localStorage.setItem('openpoke_user_id', data.user_id);
          }
        } catch {}
      } else {
        const statusText = typeof data?.status === 'string' && data.status && data.status !== 'UNKNOWN'
          ? `Status: ${data.status}`
          : 'Not connected yet.';
        setGmailStatusMessage(statusText);
        try {
          localStorage.removeItem('gmail_connected');
          localStorage.removeItem('gmail_email');
        } catch {}
      }
    } catch (e: any) {
      setGmailConnected(false);
      setGmailProfile(null);
      setGmailEmail('');
      setGmailStatusMessage(e?.message || 'Failed to check Gmail status');
    } finally {
      setIsRefreshingGmail(false);
    }
  }, [gmailConnId, readStoredConnectionRequestId, readStoredUserId]);

  const handleDisconnectGmail = useCallback(async () => {
    if (typeof window !== 'undefined') {
      const proceed = window.confirm('Disconnect Gmail from OpenPoke?');
      if (!proceed) return;
    }

    try {
      setIsDisconnecting(true);
      setGmailStatusMessage('Disconnecting Gmail…');
      const userId = readStoredUserId();
      const connectionRequestId = readStoredConnectionRequestId();
      const resp = await fetch('/api/gmail/disconnect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, connectionRequestId }),
      });
      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || !data?.ok) {
        const message = data?.error || `Failed (${resp.status})`;
        setGmailStatusMessage(message);
        return;
      }

      setGmailConnected(false);
      setGmailEmail('');
      setGmailProfile(null);
      setGmailConnId('');
      setGmailStatusMessage('Gmail disconnected.');
      try {
        localStorage.removeItem('gmail_connected');
        localStorage.removeItem('gmail_email');
        localStorage.removeItem('gmail_connection_request_id');
        localStorage.removeItem('openpoke_user_id');
      } catch {}
    } catch (e: any) {
      setGmailStatusMessage(e?.message || 'Failed to disconnect Gmail');
    } finally {
      setIsDisconnecting(false);
    }
  }, [readStoredConnectionRequestId, readStoredUserId]);

  useEffect(() => {
    setTimezone(settings.timezone);
  }, [settings]);

  useEffect(() => {
    if (!open) return;
    void refreshGmailStatus();
  }, [open, refreshGmailStatus]);

  if (!open) return null;

  const connectButtonLabel = connectingGmail ? 'Opening…' : gmailConnected ? 'Reconnect' : 'Connect Gmail';
  const refreshButtonLabel = isRefreshingGmail ? 'Refreshing…' : 'Refresh status';
  const disconnectButtonLabel = isDisconnecting ? 'Disconnecting…' : 'Disconnect';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="card w-full max-w-lg p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Settings</h2>
          <button onClick={onClose} className="rounded-md p-2 hover:bg-gray-100" aria-label="Close settings">
            ✕
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Timezone</label>
            <input
              className="input"
              type="text"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              placeholder="e.g. America/New_York, Europe/London"
              readOnly={!timezone}
            />
            <p className="mt-1 text-xs text-gray-500">
              {timezone ? 'Auto-detected from browser. Edit to override.' : 'Will be auto-detected on next page load.'}
            </p>
          </div>
          <div className="pt-2">
            <div className="mb-1 text-sm font-medium text-gray-700">Integrations</div>
            <div className="rounded-xl border border-gray-200 bg-white/70 p-4 shadow-sm">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="text-sm font-semibold text-gray-900">Gmail (via Composio)</div>
                  <p className="mt-1 text-sm text-gray-600">
                    Connect Gmail to unlock email search, drafting, and automations inside OpenPoke.
                  </p>
                </div>
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset ${
                    gmailConnected
                      ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                      : 'bg-amber-50 text-amber-700 ring-amber-200'
                  }`}
                >
                  {gmailConnected ? 'Connected' : 'Not connected'}
                </span>
              </div>

              {gmailConnected ? (
                <div className="mt-4 space-y-3 rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <div>
                    <div className="text-[11px] uppercase tracking-wide text-gray-500">Connected account</div>
                    <div className="mt-1 text-sm font-medium text-gray-900">{gmailEmail || 'Email unavailable'}</div>
                  </div>
                  {gmailProfileDetails.length > 0 && (
                    <dl className="grid grid-cols-1 gap-2 text-xs text-gray-600 sm:grid-cols-3">
                      {gmailProfileDetails.map((item) => (
                        <div key={item.label} className="rounded-md border border-gray-200 bg-white/80 p-2">
                          <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">{item.label}</dt>
                          <dd className="mt-1 text-sm font-medium text-gray-900">{item.value}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  {gmailStatusMessage && (
                    <p className="text-xs text-gray-500" aria-live="polite">{gmailStatusMessage}</p>
                  )}
                </div>
              ) : (
                <div className="mt-4 rounded-lg border border-dashed border-gray-200 p-3 text-sm text-gray-500" aria-live="polite">
                  {gmailStatusMessage || 'Complete the connection to view your Gmail account details here.'}
                </div>
              )}

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn"
                  onClick={handleConnectGmail}
                  disabled={connectingGmail || isRefreshingGmail || isDisconnecting}
                  aria-busy={connectingGmail}
                >
                  {connectButtonLabel}
                </button>
                <button
                  type="button"
                  className="rounded-md border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={refreshGmailStatus}
                  disabled={isRefreshingGmail || connectingGmail}
                  aria-busy={isRefreshingGmail}
                >
                  {refreshButtonLabel}
                </button>
                {gmailConnected && (
                  <button
                    type="button"
                    className="rounded-md border border-transparent bg-red-50 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={handleDisconnectGmail}
                    disabled={isDisconnecting || connectingGmail}
                    aria-busy={isDisconnecting}
                  >
                    {disconnectButtonLabel}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* MCP Servers Section */}
        <div className="mt-8">
          <div className="border-b border-gray-200 pb-4">
            <h3 className="text-base font-semibold text-gray-900">MCP Servers</h3>
            <p className="mt-1 text-sm text-gray-500">
              Connect to external MCP servers to access additional tools and capabilities.
            </p>
          </div>

          <div className="mt-4">
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <h4 className="text-sm font-medium text-gray-900 mb-3">Add New Server</h4>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Server Name</label>
                    <input
                      type="text"
                      value={newServerName}
                      onChange={(e) => setNewServerName(e.target.value)}
                      placeholder="e.g., zomato"
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Server URL</label>
                    <input
                      type="url"
                      value={newServerUrl}
                      onChange={(e) => setNewServerUrl(e.target.value)}
                      placeholder="https://mcp-server.example.com/mcp"
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Auth Type</label>
                    <select
                      value={newServerAuthType}
                      onChange={(e) => setNewServerAuthType(e.target.value)}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                    >
                      <option value="none">None</option>
                      <option value="api_key">API Key</option>
                      <option value="oauth">OAuth</option>
                    </select>
                  </div>
                  {newServerAuthType === 'api_key' && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">API Key</label>
                      <input
                        type="password"
                        value={newServerApiKey}
                        onChange={(e) => setNewServerApiKey(e.target.value)}
                        placeholder="Enter API key"
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                      />
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  className="btn"
                  onClick={addMcpServer}
                  disabled={loadingMcp || !newServerName || !newServerUrl}
                  aria-busy={loadingMcp}
                >
                  Add Server
                </button>
              </div>
            </div>

            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-900 mb-3">Configured Servers</h4>
              {mcpServers.length === 0 ? (
                <div className="rounded-lg border border-dashed border-gray-200 p-4 text-center text-sm text-gray-500">
                  No MCP servers configured. Add one above to get started.
                </div>
              ) : (
                <div className="space-y-3">
                  {mcpServers.map((server) => (
                    <div key={server.name} className="rounded-lg border border-gray-200 bg-white p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{server.name}</span>
                            <span
                              className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ring-1 ring-inset ${
                                server.enabled
                                  ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                                  : 'bg-amber-50 text-amber-700 ring-amber-200'
                              }`}
                            >
                              {server.enabled ? 'Enabled' : 'Disabled'}
                            </span>
                          </div>
                          <div className="mt-1 text-sm text-gray-500">{server.url}</div>
                          {server.auth_type && (
                            <div className="mt-1 text-xs text-gray-400">Auth: {server.auth_type}</div>
                          )}
                          <div className="mt-1 text-xs text-gray-400">
                            {server.tool_count} tool{server.tool_count !== 1 ? 's' : ''} available
                          </div>
                        </div>
                        <button
                          type="button"
                          className="rounded-md border border-transparent bg-red-50 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                          onClick={() => removeMcpServer(server.name)}
                          disabled={loadingMcp}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {mcpTools.length > 0 && (
              <div className="mt-6">
                <h4 className="text-sm font-medium text-gray-900 mb-3">Available Tools</h4>
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <div className="grid gap-2">
                    {mcpTools.map((tool) => (
                      <div key={tool.name} className="flex items-center justify-between rounded-md border border-gray-200 bg-white p-3">
                        <div>
                          <div className="font-medium text-gray-900">{tool.name}</div>
                          <div className="text-sm text-gray-500">{tool.description}</div>
                          <div className="text-xs text-gray-400">Server: {tool.server_name}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Cancel</button>
          <button
            className="btn"
            onClick={() => {
              onSave({ timezone });
              onClose();
            }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
