import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { getConfig, getHealth } from '../api/config';
import type { ConfigData, HealthData } from '../api/config';

interface ConfigContextValue {
  config: ConfigData | null;
  health: HealthData | null;
  isLoading: boolean;
  error: string | null;
  refreshConfig: () => Promise<void>;
}

export const ConfigContext = createContext<ConfigContextValue | undefined>(undefined);

export const ConfigProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConfigAndHealth = useCallback(async () => {
    try {
      setError(null);
      const [configRes, healthRes] = await Promise.allSettled([
        getConfig(),
        getHealth(),
      ]);

      if (configRes.status === 'fulfilled') {
        setConfig(configRes.value);
      }
      if (healthRes.status === 'fulfilled') {
        setHealth(healthRes.value);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to introspect system configuration');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfigAndHealth();
    // Periodic health polling every 30s
    const interval = setInterval(fetchConfigAndHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchConfigAndHealth]);

  return (
    <ConfigContext.Provider
      value={{
        config,
        health,
        isLoading,
        error,
        refreshConfig: fetchConfigAndHealth,
      }}
    >
      {children}
    </ConfigContext.Provider>
  );
};

export function useConfig() {
  const context = useContext(ConfigContext);
  if (!context) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
}
