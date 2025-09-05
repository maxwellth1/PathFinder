import { NextRequest, NextResponse } from 'next/server'
import { Buffer } from 'buffer'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const message = formData.get('message') as string
    const fileId = formData.get('file_id') as string

    // Validate the request
    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required and must be a string' },
        { status: 400 }
      )
    }

    if (!fileId) {
      return NextResponse.json(
        { error: 'File ID is required' },
        { status: 400 }
      )
    }

    // Create form data for backend
    const backendFormData = new FormData()
    backendFormData.append('message', message)
    backendFormData.append('file_id', fileId)

    // Create a streaming response from the FastAPI backend
    const response = await fetch(`${BACKEND_URL}/api/spreadsheet/stream`, {
      method: 'POST',
      body: backendFormData,
    })
    
    if (!response.ok) {
      const errorData = await response.text()
      console.error('Backend streaming error:', errorData)
      return NextResponse.json(
        { error: 'Failed to process streaming spreadsheet analysis request' },
        { status: response.status }
      )
    }
    
    // Create a ReadableStream to handle cleanup after streaming
    const stream = new ReadableStream({
      start(controller) {
        if (!response.body) {
          controller.close()
          return
        }
        
        const reader = response.body.getReader()
        
        function pump(): Promise<void> {
          return reader.read().then(({ done, value }) => {
            if (done) {
              controller.close()
              return
            }
            
            controller.enqueue(value)
            return pump()
          })
        }
        
        return pump()
      },
      
      cancel() {
        // No cleanup needed
      }
    })
    
    // Forward the streaming response
    return new NextResponse(stream, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    })
    
  } catch (error) {
    console.error('Streaming spreadsheet API route error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}