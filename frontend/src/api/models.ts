import { request } from './client';

export interface ModelItem {
  id: string;
  name: string;
  provider: string;
  tier: 'Local' | 'Free Tier' | 'API Key' | string;
  badge: 'Fast' | 'Quality' | 'Ultra-Fast' | 'Reasoning' | string;
  description: string;
  context_window: string;
  is_local: boolean;
  env_key?: string | null;
  is_available: boolean;
}

export async function getModels(): Promise<ModelItem[]> {
  return request<ModelItem[]>('/api/models');
}
