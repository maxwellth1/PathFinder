"use client"

import { useState, useCallback, useRef, useEffect } from 'react'

export interface SpreadsheetChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  pandasCommand?: string
  plotlyPlot?: string
}

export interface UseSpreadsheetChatOptions {
  api?: string
  streaming?: boolean
  fileId?: string | null
}

export interface UseSpreadsheetChatReturn {
  messages: SpreadsheetChatMessage[]
  input: string
  isLoading: boolean
  error: string | null
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  handleSubmit: (e: React.FormEvent) => Promise<void>
  clearMessages: () => void
  uploadedFile: File | null
  setUploadedFile: (file: File | null) => void
}

// Function to format streaming content similar to the original
const formatStreamingContent = (content: string): string => {
  // Split by common bullet point patterns and format as HTML
  const lines = content.split(/(?:^|\n)\s*[-•*]\s*/)
  
  // If we have bullet points, format them
  if (lines.length > 1) {
    // First line is usually the intro text before bullet points
    const intro = lines[0].trim()
    const bulletPoints = lines.slice(1).filter(line => line.trim())
    
    if (bulletPoints.length > 0) {
      const formattedBullets = bulletPoints
        .map(point => `• ${point.trim()}`)
        .join('\n')
      
      return intro ? `${intro}\n\n${formattedBullets}` : formattedBullets
    }
  }
  
  // If no bullet points detected, return original content
  return content
}

export function useSpreadsheetChat(options: UseSpreadsheetChatOptions = {}): UseSpreadsheetChatReturn {
  const { api = '/api/spreadsheet', streaming = false, fileId: initialFileId = null } = options
  
  const [messages, setMessages] = useState<SpreadsheetChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [uploadedFileId, setUploadedFileId] = useState<string | null>(initialFileId)

  useEffect(() => {
    if (initialFileId) {
      setUploadedFileId(initialFileId);
    }
  }, [initialFileId]);
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
    
    if (!input.trim() || isLoading || !uploadedFileId) return

    const userMessage: SpreadsheetChatMessage = {
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
      const apiUrl = streaming ? '/api/spreadsheet/stream' : api
      
      const formData = new FormData()
      formData.append('message', userMessage.content)
      formData.append('file_id', uploadedFileId)
      if (sessionId) {
        formData.append('session_id', sessionId)
      }
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData,
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
        
        const assistantMessage: SpreadsheetChatMessage = {
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
                  
                  if (data.error) {
                    throw new Error(data.error)
                  }

                  setMessages(prev => 
                    prev.map(msg => {
                      if (msg.id === assistantMessageId) {
                        const updatedMsg = { ...msg };
                        if (data.response) {
                          updatedMsg.content = formatStreamingContent(data.response);
                        }
                        if (data.pandasCommand) {
                          updatedMsg.pandasCommand = data.pandasCommand;
                        }
                        if (data.plotlyPlot) {
                          updatedMsg.plotlyPlot = data.plotlyPlot;
                        }
                        return updatedMsg;
                      }
                      return msg;
                    })
                  );

                } catch (parseError) {
                  console.warn('Failed to parse SSE data:', line)
                }
              }
            }
          }
        } finally {
          reader.releaseLock()
        }
      } else {
        const data = await response.json()
        
        const assistantMessage: SpreadsheetChatMessage = {
          id: generateMessageId(),
          role: 'assistant',
          content: data.response || 'I received your message but couldn\'t generate a proper response.',
          timestamp: new Date(),
          pandasCommand: data.pandasCommand,
          plotlyPlot: data.plotlyPlot
        }

        setMessages(prev => [...prev, assistantMessage])
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        console.error('Spreadsheet chat error:', err)
        setError(err.message || 'An error occurred while processing your message')
        
        const errorMessage: SpreadsheetChatMessage = {
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
  }, [input, isLoading, streaming, api, uploadedFileId, sessionId])

  return {
    messages,
    input,
    isLoading,
    error,
    handleInputChange,
    handleSubmit,
    clearMessages,
    uploadedFile,
    setUploadedFile,
  }
}
 