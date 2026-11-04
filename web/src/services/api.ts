// API base URL configured from environment configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}/${path.replace(/^\//, "")}`;
  
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Inject active authorization token if present
  const accessToken = localStorage.getItem("access_token");
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  }).catch(() => {
    throw new ApiError("Network error. Unable to establish connection to DeepGuard services.", 503);
  });

  if (!response.ok) {
    let errorMessage = "An unexpected error occurred.";
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        if (typeof errorJson.detail === "string") {
          errorMessage = errorJson.detail;
        } else if (Array.isArray(errorJson.detail)) {
          errorMessage = errorJson.detail.map((err: any) => err.msg).join(", ");
        }
      }
    } catch {
      if (response.status === 401) {
        errorMessage = "Session expired. Please log in again.";
      } else if (response.status === 413) {
        errorMessage = "File is too large.";
      } else if (response.status === 415) {
        errorMessage = "Unsupported file type.";
      } else if (response.status === 500) {
        errorMessage = "Analysis service failed. Check backend logs.";
      } else {
        errorMessage = `Server returned status code ${response.status}`;
      }
    }

    if (response.status === 401 && (errorMessage.toLowerCase().includes("unauthorized") || errorMessage.toLowerCase().includes("could not validate") || errorMessage.toLowerCase().includes("token"))) {
      errorMessage = "Session expired. Please log in again.";
    } else if (response.status === 413) {
      errorMessage = "File is too large.";
    } else if (response.status === 415) {
      errorMessage = "Unsupported file type.";
    } else if (response.status === 500 && (!errorMessage || errorMessage === "An unexpected error occurred." || errorMessage.includes("Internal server error"))) {
      errorMessage = "Analysis service failed. Check backend logs.";
    }

    throw new ApiError(errorMessage, response.status);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const apiService = {
  async register(name: string, email: string, password: string) {
    return request<{ message: string }>("api/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
  },

  async login(email: string, password: string) {
    const data = await request<{
      access_token: string;
      refresh_token: string;
      token_type: string;
    }>("api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    
    // Save tokens locally
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return data;
  },

  async logout() {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      try {
        await request<{ message: string }>("api/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch (err) {
        console.error("Logout request to backend failed:", err);
      }
    }
    
    // Always clear tokens locally
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },

  async refresh() {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      throw new ApiError("No session refresh token available.", 401);
    }

    try {
      const data = await request<{
        access_token: string;
        refresh_token: string;
        token_type: string;
      }>("api/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      
      localStorage.setItem("access_token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("refresh_token", data.refresh_token);
      }
      return data;
    } catch (err) {
      // Clear tokens on failed refresh to force re-auth
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      throw err;
    }
  },

  async getMe() {
    return request<{
      id: number;
      name: string;
      email: string;
      is_active: boolean;
      is_verified: boolean;
      created_at: string;
    }>("api/auth/me", {
      method: "GET",
    });
  },

  async updateProfile(name: string, version?: number) {
    return request<{
      id: number;
      name: string;
      email: string;
      is_active: boolean;
      is_verified: boolean;
      version?: number;
      created_at: string;
      updated_at?: string;
    }>("api/auth/profile", {
      method: "PUT",
      body: JSON.stringify({ name, version }),
    });
  },


  async sendOtp(email: string, purpose: string = "register") {
    return request<{ message: string }>("api/auth/send-otp", {
      method: "POST",
      body: JSON.stringify({ email, purpose }),
    });
  },

  async verifyOtp(email: string, code: string, purpose: string) {
    return request<{
      verified: boolean;
      reset_token?: string;
      message: string;
    }>("api/auth/verify-otp", {
      method: "POST",
      body: JSON.stringify({ email, code, purpose }),
    });
  },

  async forgotPassword(email: string) {
    return request<{ message: string }>("api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },

  async resetPassword(email: string, token: string, newPassword: string) {
    return request<{ message: string }>("api/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ email, token, new_password: newPassword }),
    });
  },

  // ── Analysis API ──────────────────────────────────────────────────────────

  async analyzeImage(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    // Returns full analysis detail synchronously (200 OK)
    return request<any>("api/analysis/image", {
      method: "POST",
      body: formData,
    });
  },

  async analyzeVideo(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    // Returns 202 Accepted with analysis_id to poll
    return request<any>("api/analysis/video", {
      method: "POST",
      body: formData,
    });
  },

  async analyzeAudio(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    // Returns 202 Accepted with analysis_id to poll
    return request<any>("api/analysis/audio", {
      method: "POST",
      body: formData,
    });
  },

  async getAnalysis(id: string | number) {
    return request<any>(`api/analysis/${id}`, {
      method: "GET",
    });
  },

  async getAnalysisHistory(params?: {
    page?: number;
    page_size?: number;
    media_type?: string;
    status?: string;
    prediction?: string;
  }) {
    const query = new URLSearchParams();
    if (params) {
      if (params.page) query.append("page", params.page.toString());
      if (params.page_size) query.append("page_size", params.page_size.toString());
      if (params.media_type && params.media_type !== "all") query.append("media_type", params.media_type);
      if (params.status && params.status !== "all") query.append("status", params.status);
      if (params.prediction && params.prediction !== "all") query.append("prediction", params.prediction);
    }
    const qs = query.toString();
    const url = qs ? `api/analysis/history?${qs}` : "api/analysis/history";
    return request<any>(url, {
      method: "GET",
    });
  },

  async getNotifications() {
    return request<Array<{
      id: number;
      category: string;
      title: string;
      body: string;
      is_read: boolean;
      created_at: string;
      related_analysis_id?: number | null;
    }>>("api/notifications", {
      method: "GET",
    });
  },

  async clearNotifications() {
    return request<{ message: string }>("api/notifications", {
      method: "DELETE",
    });
  },

  async deleteNotification(id: number) {
    return request<{ message: string }>(`api/notifications/${id}`, {
      method: "DELETE",
    });
  },

  async markNotificationAsRead(id: number) {
    return request<{
      id: number;
      category: string;
      title: string;
      body: string;
      is_read: boolean;
      created_at: string;
    }>(`api/notifications/${id}/read`, {
      method: "PATCH",
    });
  },

  async markAllNotificationsAsRead() {
    return request<{ message: string }>("api/notifications/read-all", {
      method: "PATCH",
    });
  },

  async getSettings() {
    return request<{
      sensitivity_tolerance: number;
      api_key: string;
      version: number;
      updated_at: string;
    }>("api/settings", {
      method: "GET",
    });
  },

  async updateSettings(data: {
    sensitivity_tolerance?: number;
    api_key?: string;
    version?: number;
  }) {
    return request<{
      sensitivity_tolerance: number;
      api_key: string;
      version: number;
      updated_at: string;
    }>("api/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async getSyncState() {
    return request<{
      server_time: string;
      user: any;
      settings: any;
      unread_notifications: number;
      total_analyses: number;
      recent_analyses: any[];
    }>("api/sync/state", {
      method: "GET",
    });
  },

  async getSubscription() {
    return request<{
      tier: string;
      status: string;
      used_analyses: number;
      total_analyses: number;
    }>("api/subscription", {
      method: "GET",
    });
  },

  async deleteAnalysis(id: string | number) {
    return request<{ message: string }>(`api/analysis/${id}`, {
      method: "DELETE",
    });
  },

  async fetchMediaBlob(path: string): Promise<string> {
    const url = `${API_BASE_URL}/${path.replace(/^\//, "")}`;
    const accessToken = localStorage.getItem("access_token");
    const headers: Record<string, string> = {};
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }
    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new ApiError(`Failed to load media (${response.status})`, response.status);
    }
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  },

  async getScanHistory(page: number = 1, pageSize: number = 20) {
    const data = await this.getAnalysisHistory({ page, page_size: pageSize });
    return { analyses: data.items || [], total: data.total || 0 };
  },

  // Investigation Cases
  async getCases(params?: { status?: string; priority?: string; search?: string }) {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.priority) query.set("priority", params.priority);
    if (params?.search) query.set("search", params.search);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return request<any[]>(`api/cases${qs}`, { method: "GET" });
  },

  async createCase(data: {
    title: string;
    description?: string;
    priority?: string;
    tags?: string;
    initial_analysis_ids?: number[];
  }) {
    return request<any>("api/cases", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async getCase(id: number | string) {
    return request<any>(`api/cases/${id}`, { method: "GET" });
  },

  async updateCase(id: number | string, data: {
    title?: string;
    description?: string;
    status?: string;
    priority?: string;
    tags?: string;
  }) {
    return request<any>(`api/cases/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async attachCaseAnalysis(id: number | string, data: { analysis_id: number; notes?: string }) {
    return request<any>(`api/cases/${id}/analyses`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async detachCaseAnalysis(caseId: number | string, analysisId: number) {
    return request<any>(`api/cases/${caseId}/analyses/${analysisId}`, {
      method: "DELETE",
    });
  },

  async addCaseNote(caseId: number | string, data: { content: string }) {
    return request<any>(`api/cases/${caseId}/notes`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async deleteCase(caseId: number | string) {
    return request<{ message: string }>(`api/cases/${caseId}`, {
      method: "DELETE",
    });
  },

  async exportCaseDossier(caseId: number | string) {
    return request<any>(`api/cases/${caseId}/export`, { method: "GET" });
  },

  // Forensic Comparison
  async compareAnalyses(id1: number, id2: number) {
    return request<any>(`api/analysis/compare?id1=${id1}&id2=${id2}`, {
      method: "GET",
    });
  },

  // Active Sessions Management
  async getSessions() {
    return request<any[]>("api/sessions", { method: "GET" });
  },

  async revokeSession(sessionId: number) {
    return request<{ message: string }>(`api/sessions/${sessionId}`, {
      method: "DELETE",
    });
  },

  async revokeOtherSessions() {
    return request<{ message: string }>("api/sessions/revoke-others", {
      method: "DELETE",
    });
  },

  // Audit Logs & Data Export
  async getAuditLogs(limit: number = 50, offset: number = 0) {
    return request<any[]>(`api/security/audit-logs?limit=${limit}&offset=${offset}`, {
      method: "GET",
    });
  },

  async downloadAccountArchive() {
    const url = `${API_BASE_URL}/api/data-export/archive`;
    const accessToken = localStorage.getItem("access_token");
    const headers: Record<string, string> = {};
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }
    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new ApiError(`Archive export failed (${response.status})`, response.status);
    }
    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = `deepguard_account_archive_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(downloadUrl);
  }
};

export const api = apiService;


