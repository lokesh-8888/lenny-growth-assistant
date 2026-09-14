/**
 * Standardized API client for the FastAPI backend with structured error envelope parsing.
 */

export interface ErrorEnvelope {
  code: string;
  message: string;
  request_id?: string;
  status_code: number;
  details?: any;
}

export class ApiError extends Error {
  status: number;
  code: string;
  requestId?: string;
  data: any;

  constructor(
    message: string,
    status: number,
    data?: any,
    code?: string,
    requestId?: string
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    this.code = code || (status === 0 ? 'NETWORK_ERROR' : `HTTP_${status}`);
    this.requestId = requestId;
  }
}

const BASE_URL = import.meta.env.VITE_API_URL || '';

export async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorData: any;
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }

      // Extract standardized error envelope fields if present
      const errorEnvelope = errorData?.error;
      const code =
        errorEnvelope?.code ||
        (response.status === 503
          ? 'SERVICE_UNAVAILABLE'
          : `HTTP_${response.status}`);
      const requestId =
        errorEnvelope?.request_id ||
        response.headers.get('X-Request-ID') ||
        undefined;
      const message =
        errorEnvelope?.message ||
        errorData?.detail ||
        `Request failed with status ${response.status} (${response.statusText})`;

      throw new ApiError(message, response.status, errorData, code, requestId);
    }

    // 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network / connection drop handling
    throw new ApiError(
      'Unable to connect to backend server. Please verify the backend service is running.',
      0,
      undefined,
      'NETWORK_ERROR'
    );
  }
}
