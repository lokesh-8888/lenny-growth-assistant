import { request } from './client';
import type { CitationItem } from './sessions';

export interface ChatRequestPayload {
  session_id?: string | null;
  message: string;
  temperature?: number;
  model?: string;
}

export interface ChatResponseData {
  session_id: string;
  message_id: string;
  role: string;
  content: string;
  citations: CitationItem[];
  served_by?: string;
  is_grounded: boolean;
}

export async function sendChatMessage(
  payload: ChatRequestPayload
): Promise<ChatResponseData> {
  return request<ChatResponseData>('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      session_id: payload.session_id || undefined,
      message: payload.message,
      temperature: payload.temperature ?? 0.7,
      model: payload.model || undefined,
    }),
  });
}
