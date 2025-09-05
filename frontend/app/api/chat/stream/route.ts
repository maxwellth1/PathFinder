import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Validate the request body
    if (!body.message || typeof body.message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required and must be a string' },
        { status: 400 }
      )
    }

    // Create a streaming response from the FastAPI backend
    const response = await fetch(`${BACKEND_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: body.message }),
    })

    if (!response.ok) {
      const errorData = await response.text()
      console.error('Backend streaming error:', errorData)
      return NextResponse.json(
        { error: 'Failed to process streaming chat request' },
        { status: response.status }
      )
    }

    // Forward the streaming response
    return new NextResponse(response.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    })

  } catch (error) {
    console.error('Streaming API route error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET() {
  return NextResponse.json({ 
    message: 'Streaming Chat API endpoint',
    methods: ['POST'],
    backend_url: BACKEND_URL,
    note: 'This endpoint supports Server-Sent Events for real-time responses'
  })
} 