"use client"

import { useState, useCallback, useRef, useEffect } from 'react'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sqlQuery?: string
}

export interface UseChatOptions {
  api?: string
  streaming?: boolean
}

export interface UseChatReturn {
  messages: ChatMessage[]
  input: string
  isLoading: boolean
  error: string | null
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  handleSubmit: (e: React.FormEvent) => Promise<void>
  clearMessages: () => void
  // Session management
  sessions: ChatSession[]
  activeSessionId: string | null
  startNewSession: () => void
  switchSession: (id: string) => void
}

interface ChatSession {
  id: string
  title: string
  createdAt: string
  updatedAt: string
}

// Function to format streaming content in real-time
const formatStreamingContent = (content: string): string => {
  // Apply real-time formatting during streaming
  let formatted = content
  
  // Handle bullet points that are being streamed
  // Convert different bullet point markers to consistent format
  formatted = formatted.replace(/^(\s*)[-•*]\s+/gm, '$1• ')
  
  // Handle mid-line bullet points (when streaming cuts in the middle)
  formatted = formatted.replace(/(\n\s*)[-•*]\s+/g, '$1• ')
  
  // Ensure proper spacing around bullet points as they appear
  // Add line break before bullet points if they don't have one
  formatted = formatted.replace(/([^\n])\n•\s+/g, '$1\n\n• ')
  
  // Handle the case where bullet points start right after text without line break
  formatted = formatted.replace(/([a-zA-Z0-9])•\s+/g, '$1\n\n• ')
  
  // Clean up excessive line breaks but preserve intentional formatting
  formatted = formatted.replace(/\n{4,}/g, '\n\n')
  
  // Ensure the content ends cleanly
  return formatted.trim()
}

export function useJewelryChat(options: UseChatOptions = {}): UseChatReturn {
  const { api = '/api/chat', streaming = false } = options
  
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessions, setSessions] = useState<ChatSession[]>([])

  const SESSIONS_KEY = 'pf_sessions'
  const ACTIVE_SESSION_KEY = 'pf_active_session'
  const messagesKeyFor = (id: string) => `pf_messages_${id}`

  // Generate a session ID when the component mounts
  useEffect(() => {
    try {
      const storedSessions = localStorage.getItem(SESSIONS_KEY)
      if (storedSessions) {
        setSessions(JSON.parse(storedSessions))
      }
      const storedActive = localStorage.getItem(ACTIVE_SESSION_KEY)
      if (storedActive) {
        setSessionId(storedActive)
        const raw = localStorage.getItem(messagesKeyFor(storedActive))
        if (raw) {
          setMessages(JSON.parse(raw))
        }
      } else {
        const newId = crypto.randomUUID()
        setSessionId(newId)
        localStorage.setItem(ACTIVE_SESSION_KEY, newId)
        // Seed a placeholder session so it appears in sidebar
        const now = new Date().toISOString()
        const initial: ChatSession = { id: newId, title: 'New Chat', createdAt: now, updatedAt: now }
        setSessions(prev => {
          const next = [initial, ...prev]
          localStorage.setItem(SESSIONS_KEY, JSON.stringify(next))
          return next
        })
      }
    } catch {}
  }, [])

  // Persist messages when they change
  useEffect(() => {
    try {
      if (sessionId) {
        localStorage.setItem(messagesKeyFor(sessionId), JSON.stringify(messages))
      }
    } catch {}
  }, [messages, sessionId])

  const generateMessageId = () => {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value)
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!input.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: generateMessageId(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setError(null)

    // Ensure session metadata exists and is updated
    try {
      if (sessionId) {
        setSessions(prev => {
          const now = new Date().toISOString()
          const exists = prev.find(s => s.id === sessionId)
          let next: ChatSession[]
          if (exists) {
            const updated = prev.map(s => s.id === sessionId ? {
              ...s,
              title: s.title === 'New Chat' ? userMessage.content.slice(0, 60) : s.title,
              updatedAt: now
            } : s)
            next = updated
          } else {
            next = [{ id: sessionId, title: userMessage.content.slice(0, 60), createdAt: now, updatedAt: now }, ...prev]
          }
          localStorage.setItem(SESSIONS_KEY, JSON.stringify(next))
          localStorage.setItem(ACTIVE_SESSION_KEY, sessionId)
          return next
        })
      }
    } catch {}

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    abortControllerRef.current = new AbortController()

    try {
      const apiUrl = streaming ? '/api/chat/stream' : api
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage.content, session_id: sessionId }),
        signal: abortControllerRef.current?.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      if (streaming) {
        if (!response.body) {
          throw new Error('No response body for streaming')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        const assistantMessageId = generateMessageId()
        let assistantContent = ''

        const assistantMessage: ChatMessage = {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          timestamp: new Date()
        }

        setMessages(prev => [...prev, assistantMessage])

        try {
          while (true) {
            const { value, done } = await reader.read()
            if (done) break

            const chunk = decoder.decode(value)
            const lines = chunk.split('\n')

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6))
                  
                  if (data.response) {
                    // Update the content with the streamed response
                    assistantContent = data.response
                    
                    // Apply real-time formatting to the streaming content
                    const formattedContent = formatStreamingContent(assistantContent)
                    
                    setMessages(prev =>
                      prev.map(msg =>
                        msg.id === assistantMessageId
                          ? { ...msg, content: formattedContent, sqlQuery: data.sqlQuery }
                          : msg
                      )
                    )
                  }
                  
                  if (data.error) {
                    throw new Error(data.error)
                  }
                } catch (parseError) {
                  console.warn('Failed to parse SSE data:', line)
                }
              }
            }
          }
        } finally {
          reader.releaseLock()
        }

        if (!assistantContent) {
          assistantContent = 'I processed your request but couldn\'t generate a response.'
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMessageId
                ? { ...msg, content: assistantContent, sqlQuery: undefined }
                : msg
            )
          )
        }
      } else {
        const data = await response.json()
        
        const assistantMessage: ChatMessage = {
          id: generateMessageId(),
          role: 'assistant',
          content: data.response || 'I received your message but couldn\'t generate a proper response.',
          timestamp: new Date(),
          sqlQuery: data.sqlQuery,
        }

        setMessages(prev => [...prev, assistantMessage])
      }
      // Update session updatedAt on any assistant response
      try {
        if (sessionId) {
          setSessions(prev => {
            const now = new Date().toISOString()
            const updated = prev.map(s => s.id === sessionId ? { ...s, updatedAt: now } : s)
            localStorage.setItem(SESSIONS_KEY, JSON.stringify(updated))
            return updated
          })
        }
      } catch {}
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        console.error('Chat error:', err)
        setError(err.message || 'An error occurred while processing your message')
        
        const errorMessage: ChatMessage = {
          id: generateMessageId(),
          role: 'assistant',
          content: 'I apologize, but I encountered an error while processing your request. Please try again.',
          timestamp: new Date()
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }, [input, isLoading, streaming, api])

  const startNewSession = useCallback(() => {
    const newId = crypto.randomUUID()
    setSessionId(newId)
    setMessages([])
    try {
      localStorage.setItem(ACTIVE_SESSION_KEY, newId)
      const now = new Date().toISOString()
      setSessions(prev => {
        const next = [{ id: newId, title: 'New Chat', createdAt: now, updatedAt: now }, ...prev]
        localStorage.setItem(SESSIONS_KEY, JSON.stringify(next))
        return next
      })
    } catch {}
  }, [])

  const switchSession = useCallback((id: string) => {
    setSessionId(id)
    try {
      localStorage.setItem(ACTIVE_SESSION_KEY, id)
      const raw = localStorage.getItem(messagesKeyFor(id))
      setMessages(raw ? JSON.parse(raw) : [])
    } catch {
      setMessages([])
    }
  }, [])

  return {
    messages,
    input,
    isLoading,
    error,
    handleInputChange,
    handleSubmit,
    clearMessages,
    sessions,
    activeSessionId: sessionId,
    startNewSession,
    switchSession
  }
} 