import { request } from './client';

export interface SessionItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SessionDetail {
  id: string;
  title: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CitationItem {
  guest?: string;
  episode_title?: string;
  source_url?: string;
  timestamp?: string;
  speaker?: string;
  quote?: string;
  quote_snippet?: string;
}

export interface MessageItem {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | string;
  content: string;
  citations: CitationItem[];
  served_by?: string;
  created_at: string;
}

export async function listSessions(): Promise<SessionItem[]> {
  return request<SessionItem[]>('/api/sessions');
}

export async function createSession(title?: string, metadata?: Record<string, any>): Promise<SessionDetail> {
  return request<SessionDetail>('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({ title, metadata }),
  });
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  return request<SessionDetail>(`/api/sessions/${sessionId}`);
}

export async function deleteSession(sessionId: string): Promise<void> {
  return request<void>(`/api/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}

export async function getSessionMessages(sessionId: string): Promise<MessageItem[]> {
  return request<MessageItem[]>(`/api/sessions/${sessionId}/messages`);
}
