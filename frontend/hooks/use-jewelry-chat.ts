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

  // Generate a session ID when the component mounts
  useEffect(() => {
    if (!sessionId) {
      setSessionId(crypto.randomUUID());
    }
  }, [sessionId]);

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
          sqlQuery: data.sqlQuery
        }

        setMessages(prev => [...prev, assistantMessage])
      }
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

  return {
    messages,
    input,
    isLoading,
    error,
    handleInputChange,
    handleSubmit,
    clearMessages
  }
} 