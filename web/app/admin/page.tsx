'use client';

import { useCallback, useEffect, useState } from 'react';

interface InteractionAgentStatus {
  status: 'active' | 'idle';
  last_activity: string | null;
  total_messages_processed: number;
}

interface RunningAgent {
  name: string;
  started_at: string;
  instructions: string;
  elapsed_seconds: number;
}

interface ExecutionAgentStats {
  total_spawned: number;
  total_completed: number;
  total_failed: number;
}

interface AdminStatus {
  interaction_agent: InteractionAgentStatus;
  execution_agents: {
    currently_running: number;
    running_agents: RunningAgent[];
    statistics: ExecutionAgentStats;
    roster: string[];
  };
}

export default function AdminDashboard() {
  const [status, setStatus] = useState<AdminStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/admin/status');
      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.status}`);
      }
      
      const data = await response.json();
      setStatus(data);
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Failed to fetch admin status:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const formatElapsedTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
      return `${Math.round(seconds / 60)}m`;
    } else {
      return `${Math.round(seconds / 3600)}h`;
    }
  };

  const formatLastActivity = (timestamp: string | null): string => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    
    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
    return date.toLocaleString();
  };

  if (loading && !status) {
    return (
      <main className="min-h-screen bg-gray-50 p-4 sm:p-6">
        <div className="mx-auto max-w-6xl">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading admin dashboard...</p>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 p-4 sm:p-6">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-sm text-gray-600">
              Monitor interaction and execution agent status
            </p>
          </div>
          <div className="flex items-center gap-4">
            {lastRefresh && (
              <p className="text-sm text-gray-500">
                Last updated: {lastRefresh.toLocaleTimeString()}
              </p>
            )}
            <button
              onClick={fetchStatus}
              disabled={loading}
              className="btn"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 rounded-md bg-red-50 p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="mt-2 text-sm text-red-700">{error}</div>
              </div>
            </div>
          </div>
        )}

        {status && (
          <div className="space-y-6">
            {/* Interaction Agent Status */}
            <div className="card">
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Interaction Agent</h2>
                <p className="text-sm text-gray-600">Main conversation handler status</p>
              </div>
              
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="flex items-center">
                    <span
                      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ring-1 ring-inset ${
                        status.interaction_agent.status === 'active'
                          ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                          : 'bg-amber-50 text-amber-700 ring-amber-200'
                      }`}
                    >
                      {status.interaction_agent.status === 'active' ? 'Active' : 'Idle'}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-gray-600">Status</p>
                </div>
                
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="text-2xl font-bold text-gray-900">
                    {status.interaction_agent.total_messages_processed.toLocaleString()}
                  </div>
                  <p className="text-sm text-gray-600">Messages Processed</p>
                </div>
                
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="text-sm font-medium text-gray-900">
                    {formatLastActivity(status.interaction_agent.last_activity)}
                  </div>
                  <p className="text-sm text-gray-600">Last Activity</p>
                </div>
              </div>
            </div>

            {/* Execution Agents */}
            <div className="card">
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Execution Agents</h2>
                <p className="text-sm text-gray-600">Background task execution agents</p>
              </div>

              {/* Summary Cards */}
              <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-4">
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="text-2xl font-bold text-blue-600">
                    {status.execution_agents.currently_running}
                  </div>
                  <p className="text-sm text-gray-600">Currently Running</p>
                </div>
                
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="text-2xl font-bold text-gray-900">
                    {status.execution_agents.statistics.total_spawned}
                  </div>
                  <p className="text-sm text-gray-600">Total Spawned</p>
                </div>
                
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="text-2xl font-bold text-emerald-600">
                    {status.execution_agents.statistics.total_completed}
                  </div>
                  <p className="text-sm text-gray-600">Completed</p>
                </div>
                
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="text-2xl font-bold text-red-600">
                    {status.execution_agents.statistics.total_failed}
                  </div>
                  <p className="text-sm text-gray-600">Failed</p>
                </div>
              </div>

              {/* Currently Running Agents */}
              {status.execution_agents.running_agents.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-md font-medium text-gray-900 mb-3">Currently Running</h3>
                  <div className="overflow-hidden rounded-lg border border-gray-200">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Agent Name
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Started
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Duration
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Instructions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {status.execution_agents.running_agents.map((agent, index) => (
                          <tr key={index}>
                            <td className="px-4 py-3 text-sm font-medium text-gray-900">
                              {agent.name}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {new Date(agent.started_at).toLocaleTimeString()}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {formatElapsedTime(agent.elapsed_seconds)}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {agent.instructions}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Agent Roster */}
              <div>
                <h3 className="text-md font-medium text-gray-900 mb-3">All Agents ({status.execution_agents.roster.length})</h3>
                {status.execution_agents.roster.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {status.execution_agents.roster.map((agentName, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-800"
                      >
                        {agentName}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-gray-200 p-4 text-center text-sm text-gray-500">
                    No agents in roster
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
