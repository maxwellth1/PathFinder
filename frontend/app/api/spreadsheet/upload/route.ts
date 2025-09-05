import { NextRequest, NextResponse } from 'next/server'
import { Buffer } from 'buffer'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get('file') as File

    if (!file) {
      return NextResponse.json(
        { error: 'File is required' },
        { status: 400 }
      )
    }

    const validTypes = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/csv']
    const validExtensions = ['.xlsx', '.csv']
    const isValidType = validTypes.includes(file.type) || validExtensions.some(ext => file.name.endsWith(ext))
    
    if (!isValidType) {
      return NextResponse.json(
        { error: 'Invalid file type. Only .xlsx and .csv files are supported' },
        { status: 400 }
      )
    }

    const bytes = await file.arrayBuffer()
    const buffer = Buffer.from(bytes)

    const backendFormData = new FormData()
    backendFormData.append('file', new Blob([buffer]), file.name)

    const response = await fetch(`${BACKEND_URL}/api/spreadsheet/upload`, {
      method: 'POST',
      body: backendFormData,
    })

    if (!response.ok) {
      const errorData = await response.text()
      console.error('Backend file upload error:', errorData)
      return NextResponse.json(
        { error: 'Failed to upload file to backend' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('Frontend file upload API route error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
