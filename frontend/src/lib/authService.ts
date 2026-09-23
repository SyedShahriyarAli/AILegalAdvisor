
/**
 * Authentication Service
 * Uses backend Flask API endpoints and keeps lightweight local cache.
 */

import { apiUrl } from './apiBase';
export type User = {
  id: string;
  name: string;
  email: string;
  organization?: string;
  firmName?: string;
  createdAt?: string;
};

/** One saved Case Analyzer run (persisted to MongoDB via /api/user-data). */
export type CaseAnalyzerSession = {
  id: string;
  title: string;
  createdAt: string;
  narrative: string;
  ocrText?: string;
  /** Full JSON response from POST /api/workspace/analyze */
  analysis: Record<string, unknown>;
  /** Last wizard step the user reached (1 intake, 2 audit, 3 merit) */
  step: number;
};

export type UserData = {
  sources: any[];
  chatHistory: any[];
  caseAnalyzerSessions: CaseAnalyzerSession[];
};

const TOKEN_KEY = 'ai_legal_advisor_token';
const USER_KEY = 'ai_legal_advisor_current_user';
const USER_DATA_PREFIX = 'ai_legal_advisor_data_';

function mergeSessionLists(a: CaseAnalyzerSession[], b: CaseAnalyzerSession[]): CaseAnalyzerSession[] {
  const map = new Map<string, CaseAnalyzerSession>();
  for (const s of [...a, ...b]) {
    if (!s?.id) continue;
    const prev = map.get(s.id);
    if (!prev || String(s.createdAt || '') >= String(prev.createdAt || '')) {
      map.set(s.id, s);
    }
  }
  return Array.from(map.values()).sort(
    (x, y) => new Date(y.createdAt).getTime() - new Date(x.createdAt).getTime(),
  );
}

const normalizeUserData = (parsed: any): UserData => ({
  sources: (parsed?.sources || []).map((s: any) => ({
    ...s,
    timestamp: s.timestamp ? new Date(s.timestamp) : new Date(),
  })),
  chatHistory: (parsed?.chatHistory || []).map((m: any) => ({
    ...m,
    timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
  })),
  caseAnalyzerSessions: parsed?.caseAnalyzerSessions || [],
});

export const authService = {
  // ─── Register ───
  register: async (userData: { name: string; email: string; password: string; organization?: string }): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await fetch(apiUrl('/api/auth/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData),
      });
      const data = await res.json();
      return data;
    } catch {
      return { success: false, error: 'Network error. Please try again.' };
    }
  },

  // ─── Login ───
  login: async (email: string, password: string): Promise<{ success: boolean; user?: User; error?: string }> => {
    try {
      const res = await fetch(apiUrl('/api/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();

      if (data.success && data.user && data.token) {
        localStorage.setItem(TOKEN_KEY, data.token);
        localStorage.setItem(USER_KEY, JSON.stringify({
          ...data.user,
          firmName: data.user.organization,
        }));
      }

      return data;
    } catch {
      return { success: false, error: 'Network error. Please try again.' };
    }
  },

  // ─── Logout ───
  logout: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      try {
        await fetch(apiUrl('/api/auth/logout'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        });
      } catch { /* ignore */ }
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  // ─── Get Current User (from local cache) ───
  getCurrentUser: (): User | null => {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  },

  // ─── Reset Password ───
  resetPassword: async (email: string, newPassword: string): Promise<boolean> => {
    try {
      const res = await fetch(apiUrl('/api/auth/reset-password'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, newPassword }),
      });
      const data = await res.json();
      return data.success;
    } catch {
      return false;
    }
  },

  // ─── Update Email ───
  updateEmail: async (oldEmail: string, newEmail: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await fetch(apiUrl('/api/auth/update-email'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ oldEmail, newEmail }),
      });
      const data = await res.json();

      if (data.success) {
        // Update local cache
        const user = authService.getCurrentUser();
        if (user && user.email === oldEmail) {
          user.email = newEmail;
          localStorage.setItem(USER_KEY, JSON.stringify(user));
        }
      }

      return data;
    } catch {
      return { success: false, error: 'Network error.' };
    }
  },

  // ─── Save User Workspace Data (sources & chats — stays in localStorage for now) ───
  saveUserData: (userId: string, data: UserData) => {
    const payload = {
      ...data,
      caseAnalyzerSessions: data.caseAnalyzerSessions || [],
      sources: (data.sources || []).map((s) => ({
        ...s,
        timestamp: s.timestamp instanceof Date ? s.timestamp.toISOString() : s.timestamp
      })),
      chatHistory: (data.chatHistory || []).map((m: any) => ({
        ...m,
        timestamp: m.timestamp instanceof Date ? m.timestamp.toISOString() : m.timestamp
      }))
    };
    localStorage.setItem(`${USER_DATA_PREFIX}${userId}`, JSON.stringify(payload));
    fetch(apiUrl(`/api/user-data/${userId}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: payload }),
    }).catch(() => { });
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('case-analyzer-history-updated'));
    }
  },

  addSource: (userId: string, source: any) => {
    const data = authService.loadUserData(userId);
    const existing = data.sources || [];
    const updated = [source, ...existing.filter(s => s.id !== source.id)];
    authService.saveUserData(userId, { ...data, sources: updated });
  },

  addCaseAnalyzerSession: (userId: string, session: CaseAnalyzerSession) => {
    const data = authService.loadUserData(userId);
    const existing = data.caseAnalyzerSessions || [];
    const updated = [session, ...existing.filter(s => s.id !== session.id)];
    authService.saveUserData(userId, { ...data, caseAnalyzerSessions: updated });
  },

  deleteCaseAnalyzerSession: (userId: string, sessionId: string) => {
    const data = authService.loadUserData(userId);
    const updated = (data.caseAnalyzerSessions || []).filter(s => s.id !== sessionId);
    authService.saveUserData(userId, { ...data, caseAnalyzerSessions: updated });
  },

  deleteAllCaseAnalyzerSessions: (userId: string) => {
    const data = authService.loadUserData(userId);
    authService.saveUserData(userId, { ...data, caseAnalyzerSessions: [] });
  },

  // ─── Load User Workspace Data ───
  loadUserData: (userId: string): UserData => {
    const data = localStorage.getItem(`${USER_DATA_PREFIX}${userId}`);
    const parsed = data ? JSON.parse(data) : { sources: [], chatHistory: [], caseAnalyzerSessions: [] };
    return normalizeUserData(parsed);
  },

  getUserData: async (userId: string): Promise<UserData> => {
    const local = authService.loadUserData(userId);
    try {
      const res = await fetch(apiUrl(`/api/user-data/${userId}`));
      const payload = await res.json();
      if (payload.success && payload.data != null) {
        const remote = normalizeUserData(payload.data);
        const remoteSourcesEmpty = (remote.sources?.length ?? 0) === 0;
        const localSourcesNonEmpty = (local.sources?.length ?? 0) > 0;

        // Server row can have chatHistory but never saved sources — keep local file uploads.
        if (remoteSourcesEmpty && localSourcesNonEmpty) {
          const merged: UserData = {
            sources: local.sources,
            chatHistory:
              (remote.chatHistory?.length ?? 0) > (local.chatHistory?.length ?? 0)
                ? remote.chatHistory
                : local.chatHistory,
            caseAnalyzerSessions: mergeSessionLists(
              local.caseAnalyzerSessions || [],
              remote.caseAnalyzerSessions || [],
            ),
          };
          authService.saveUserData(userId, merged);
          return merged;
        }

        const remoteEmpty =
          (remote.sources?.length ?? 0) === 0 &&
          (remote.chatHistory?.length ?? 0) === 0 &&
          (remote.caseAnalyzerSessions?.length ?? 0) === 0;
        const localHasData =
          (local.sources?.length ?? 0) > 0 ||
          (local.chatHistory?.length ?? 0) > 0 ||
          (local.caseAnalyzerSessions?.length ?? 0) > 0;
        if (remoteEmpty && localHasData) {
          return local;
        }

        const mergedRemote: UserData = {
          ...remote,
          caseAnalyzerSessions: mergeSessionLists(
            local.caseAnalyzerSessions || [],
            remote.caseAnalyzerSessions || [],
          ),
        };
        authService.saveUserData(userId, mergedRemote);
        return mergedRemote;
      }
    } catch {
      // fallback to local cache
    }
    return local;
  },
};
