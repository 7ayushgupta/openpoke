const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8001';

interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  ok: boolean;
}

class ApiClient {
  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('openpoke_token');
  }

  private async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const token = this.getToken();
    
    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
    };

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, config);
      
      if (!response.ok) {
        if (response.status === 401) {
          // Token expired or invalid, redirect to login
          localStorage.removeItem('openpoke_token');
          window.location.href = '/login';
          return { ok: false, error: 'Unauthorized' };
        }
        
        const errorData = await response.json().catch(() => ({}));
        return { 
          ok: false, 
          error: errorData.error || `HTTP ${response.status}` 
        };
      }

      const data = await response.json().catch(() => null);
      return { ok: true, data };
    } catch (error) {
      return { 
        ok: false, 
        error: error instanceof Error ? error.message : 'Network error' 
      };
    }
  }

  // Chat API
  async sendMessage(messages: any[]) {
    return this.request('/api/v1/chat/send', {
      method: 'POST',
      body: JSON.stringify({ messages }),
    });
  }

  async getChatHistory() {
    return this.request('/api/v1/chat/history');
  }

  async clearChatHistory() {
    return this.request('/api/v1/chat/history', {
      method: 'DELETE',
    });
  }

  // Auth API
  async getCurrentUser() {
    return this.request('/api/v1/auth/me');
  }

  async logout() {
    return this.request('/api/v1/auth/logout', {
      method: 'POST',
    });
  }

  // Gmail API
  async connectGmail(payload: any) {
    return this.request('/api/v1/gmail/connect', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async disconnectGmail() {
    return this.request('/api/v1/gmail/disconnect', {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async getGmailStatus() {
    return this.request('/api/v1/gmail/status', {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  // MCP API
  async listMcpServers() {
    return this.request('/api/v1/mcp/servers');
  }

  async addMcpServer(payload: any) {
    return this.request('/api/v1/mcp/servers', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async deleteMcpServer(serverName: string) {
    return this.request(`/api/v1/mcp/servers/${encodeURIComponent(serverName)}`, {
      method: 'DELETE',
    });
  }

  async getMcpTools() {
    return this.request('/api/v1/mcp/tools');
  }

  // Timezone API
  async setTimezone(timezone: string) {
    return this.request('/api/v1/meta/timezone', {
      method: 'POST',
      body: JSON.stringify({ timezone }),
    });
  }
}

export const apiClient = new ApiClient();
export default apiClient;

