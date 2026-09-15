import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  listSessions,
  createSession,
  deleteSession,
  getSessionMessages,
} from '../api/sessions';
import type { SessionItem, MessageItem } from '../api/sessions';
import { sendChatMessage } from '../api/chat';
import { generateArtifact, getSessionArtifacts, getArtifact } from '../api/artifacts';
import type { ArtifactData } from '../components/ArtifactViewer';
import { ModelContext } from './ModelContext';

interface ChatContextValue {
  sessions: SessionItem[];
  activeSessionId: string | null;
  messages: MessageItem[];
  activeArtifact: ArtifactData | null;
  isChatLoading: boolean;
  isArtifactGenerating: boolean;
  generatingType: string | null;
  error: string | null;
  startNewChat: () => Promise<void>;
  selectSession: (sessionId: string) => Promise<void>;
  removeSession: (sessionId: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  generateArtifactAction: (
    type: 'ship30' | 'markdown' | 'html',
    title?: string,
    messageId?: string
  ) => Promise<void>;
  openArtifact: (artifact: ArtifactData) => void;
  closeArtifact: () => void;
  clearError: () => void;
}

const ChatContext = createContext<ChatContextValue | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [activeArtifact, setActiveArtifact] = useState<ArtifactData | null>(null);
  const [isChatLoading, setIsChatLoading] = useState<boolean>(false);
  const [isArtifactGenerating, setIsArtifactGenerating] = useState<boolean>(false);
  const [generatingType, setGeneratingType] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const modelCtx = useContext(ModelContext);
  const getActiveModelId = useCallback(() => {
    return modelCtx?.selectedModelId;
  }, [modelCtx?.selectedModelId]);

  // Load initial session list
  const loadSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data);
      // If we have sessions and none is selected, select the most recent
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id);
      }
    } catch (err: any) {
      console.error('Failed to fetch sessions:', err);
    }
  }, [activeSessionId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Load messages when activeSessionId changes
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }

    let isMounted = true;
    const fetchHistory = async () => {
      try {
        const msgs = await getSessionMessages(activeSessionId);
        if (isMounted) {
          setMessages((prev) => {
            if (prev.length > 0 && prev[0].session_id === activeSessionId) {
              const newMsgs = prev.filter((p) => !msgs.some((m) => m.id === p.id));
              return [...msgs, ...newMsgs];
            }
            return msgs;
          });
        }
        // Also fetch any existing artifacts for this session
        const artifacts = await getSessionArtifacts(activeSessionId);
        if (isMounted && artifacts.length > 0 && !activeArtifact) {
          try {
            const full = await getArtifact(artifacts[0].id);
            if (isMounted) {
              setActiveArtifact({
                id: full.id,
                session_id: full.session_id,
                type: full.type,
                title: full.title,
                content: full.content,
                word_count: full.word_count,
                citations: full.citations,
                created_at: full.created_at,
              });
            }
          } catch {
            if (isMounted) {
              setActiveArtifact({
                id: artifacts[0].id,
                session_id: artifacts[0].session_id,
                type: artifacts[0].type,
                title: artifacts[0].title,
                content: '',
                word_count: artifacts[0].word_count,
              });
            }
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err?.message || 'Failed to load conversation history');
        }
      }
    };

    fetchHistory();
    return () => {
      isMounted = false;
    };
  }, [activeSessionId]);

  const startNewChat = useCallback(async () => {
    setError(null);
    try {
      const newSession = await createSession('New Growth Consultation');
      setSessions((prev) => [
        {
          id: newSession.id,
          title: newSession.title,
          created_at: newSession.created_at,
          updated_at: newSession.updated_at,
          message_count: 0,
        },
        ...prev,
      ]);
      setActiveSessionId(newSession.id);
      setMessages([]);
      setActiveArtifact(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to create new chat session');
    }
  }, []);

  const selectSession = useCallback(async (sessionId: string) => {
    if (sessionId === activeSessionId) return;
    setActiveSessionId(sessionId);
    setError(null);
  }, [activeSessionId]);

  const removeSession = useCallback(async (sessionId: string) => {
    setError(null);
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setMessages([]);
        setActiveArtifact(null);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to delete session');
    }
  }, [activeSessionId]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isChatLoading) return;
      setError(null);
      setIsChatLoading(true);

      let currentSessionId = activeSessionId;

      // If no session exists yet, create one automatically
      if (!currentSessionId) {
        try {
          const newSession = await createSession(content.slice(0, 40));
          currentSessionId = newSession.id;
          setActiveSessionId(newSession.id);
          setSessions((prev) => [
            {
              id: newSession.id,
              title: newSession.title,
              created_at: newSession.created_at,
              updated_at: newSession.updated_at,
              message_count: 0,
            },
            ...prev,
          ]);
        } catch (err: any) {
          setError(err?.message || 'Failed to initiate conversation session');
          setIsChatLoading(false);
          return;
        }
      }

      // Optimistic user message
      const tempUserMessage: MessageItem = {
        id: `temp-${Date.now()}`,
        session_id: currentSessionId,
        role: 'user',
        content,
        citations: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, tempUserMessage]);

      try {
        const chatPayload: { session_id: string; message: string; model?: string } = {
          session_id: currentSessionId,
          message: content,
        };
        const activeModel = getActiveModelId();
        if (activeModel) {
          chatPayload.model = activeModel;
        }
        const response = await sendChatMessage(chatPayload);

        const assistantMessage: MessageItem = {
          id: response.message_id,
          session_id: response.session_id,
          role: response.role,
          content: response.content,
          citations: response.citations || [],
          served_by: response.served_by,
          created_at: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // Refresh session list to update message count / timestamp
        const updatedSessions = await listSessions();
        setSessions(updatedSessions);
      } catch (err: any) {
        setError(err?.message || 'Failed to generate assistant response');
      } finally {
        setIsChatLoading(false);
      }
    },
    [activeSessionId, isChatLoading]
  );

  const generateArtifactAction = useCallback(
    async (type: 'ship30' | 'markdown' | 'html', title?: string, messageId?: string) => {
      if (!activeSessionId) {
        setError('No active session to generate an artifact from.');
        return;
      }
      setError(null);
      setIsArtifactGenerating(true);
      setGeneratingType(type);

      try {
        const artifactPayload: {
          session_id: string;
          type: 'ship30' | 'markdown' | 'html';
          title?: string;
          source_message_id?: string;
          model?: string;
        } = {
          session_id: activeSessionId,
          type,
          title,
          source_message_id: messageId,
        };
        const activeModel = getActiveModelId();
        if (activeModel) {
          artifactPayload.model = activeModel;
        }
        const response = await generateArtifact(artifactPayload);

        setActiveArtifact({
          id: response.id,
          session_id: response.session_id,
          type: response.type,
          title: response.title,
          content: response.content,
          word_count: response.word_count,
          citations: response.citations,
          created_at: response.created_at,
        });
      } catch (err: any) {
        setError(err?.message || `Failed to generate ${type} artifact`);
      } finally {
        setIsArtifactGenerating(false);
        setGeneratingType(null);
      }
    },
    [activeSessionId]
  );

  const openArtifact = useCallback((artifact: ArtifactData) => {
    setActiveArtifact(artifact);
  }, []);

  const closeArtifact = useCallback(() => {
    setActiveArtifact(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return (
    <ChatContext.Provider
      value={{
        sessions,
        activeSessionId,
        messages,
        activeArtifact,
        isChatLoading,
        isArtifactGenerating,
        generatingType,
        error,
        startNewChat,
        selectSession,
        removeSession,
        sendMessage,
        generateArtifactAction,
        openArtifact,
        closeArtifact,
        clearError,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}
