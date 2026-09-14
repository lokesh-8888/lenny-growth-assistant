import { request } from './client';
import type { CitationItem } from './sessions';

export interface ArtifactGeneratePayload {
  session_id: string;
  type: 'ship30' | 'markdown' | 'html' | string;
  title?: string;
  source_message_id?: string;
}

export interface ArtifactResponseData {
  id: string;
  session_id?: string;
  type: string;
  title: string;
  content: string;
  word_count: number;
  validation?: any;
  citations: CitationItem[];
  served_by?: string;
  created_at: string;
}

export interface ArtifactListItemData {
  id: string;
  session_id?: string;
  type: string;
  title: string;
  word_count: number;
  created_at: string;
}

export async function generateArtifact(
  payload: ArtifactGeneratePayload
): Promise<ArtifactResponseData> {
  return request<ArtifactResponseData>('/api/artifacts/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getSessionArtifacts(
  sessionId: string
): Promise<ArtifactListItemData[]> {
  return request<ArtifactListItemData[]>(`/api/sessions/${sessionId}/artifacts`);
}

export async function getArtifact(
  artifactId: string
): Promise<ArtifactResponseData> {
  return request<ArtifactResponseData>(`/api/artifacts/${artifactId}`);
}
