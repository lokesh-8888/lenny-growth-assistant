import { request } from './client';

export interface ConfigData {
  current_provider: string;
  current_model: string;
  fallback_provider?: string;
  fallback_model?: string;
  available_providers: string[];
  cloud_configured: boolean;
}

export interface HealthData {
  status: 'healthy' | 'degraded' | 'unhealthy' | string;
  dependencies: {
    postgres: {
      status: string;
      latency_ms?: number;
      error?: string | null;
    };
    ollama: {
      status: string;
      models_available?: string | string[];
      error?: string | null;
    };
    cloud_llm?: {
      provider?: string | null;
      configured: boolean;
    };
  };
}

export async function getConfig(): Promise<ConfigData> {
  return request<ConfigData>('/api/config');
}

export async function getHealth(): Promise<HealthData> {
  return request<HealthData>('/health');
}
