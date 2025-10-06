"use client"
import { useState, useCallback, useRef } from 'react'
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Home,
  LayoutGrid,
  Gem,
  ShieldCheck,
  CircleDollarSign,
  Tag,
  ArrowDownToLine,
  Users,
  UserSquare,
  Box,
  ClipboardList,
  Settings,
  Bot,
  Mic,
  Send,
  HelpCircle,
  Search,
  ChevronRight,
  Plus,
  User,
  Upload,
  FileSpreadsheet,
  X,
  Clipboard,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useRouter } from 'next/navigation'
import { useSpreadsheetChat, SpreadsheetChatMessage } from "@/hooks/use-spreadsheet-chat"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import '@/styles/markdown.css'
import PlotlyChart from '@/components/ui/plotly-chart'
import Image from 'next/image'


const navItems = [
  { icon: Home, label: "Home" },
  { icon: LayoutGrid, label: "Dashboard" },
  { icon: Gem, label: "Jewellery" },
  { icon: ShieldCheck, label: "Plans" },
  { icon: CircleDollarSign, label: "Sales" },
  { icon: Tag, label: "Booking" },
  { icon: ArrowDownToLine, label: "Inventory" },
  { icon: Users, label: "Orders" },
  { icon: UserSquare, label: "Customer" },
  { icon: Box, label: "Box" },
  { icon: ClipboardList, label: "Reports" },
  { icon: Settings, label: "Settings" },
]

interface FileUploadProps {
  onFileUpload: (file: File) => void
  isUploading: boolean
  error: string | null
}

function FileUpload({ onFileUpload, isUploading, error }: FileUploadProps) {
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      const validTypes = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/csv']
      if (validTypes.includes(file.type) || file.name.endsWith('.xlsx') || file.name.endsWith('.csv')) {
        onFileUpload(file)
      } else {
        alert('Please select a valid Excel (.xlsx) or CSV (.csv) file')
      }
    }
  }

  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
      <div className="bg-white/10 p-8 rounded-2xl mb-6 border-2 border-dashed border-white/20 hover:border-white/30 transition-colors">
        <FileSpreadsheet className="h-16 w-16 mx-auto mb-4 text-white/70" />
        <h2 className="text-2xl font-bold mb-2">Upload Your Spreadsheet</h2>
        <p className="text-gray-400 mb-6">Upload an Excel (.xlsx) or CSV (.csv) file to start analyzing your data</p>
        
        <input
          type="file"
          accept=".xlsx,.csv"
          onChange={handleFileSelect}
          className="hidden"
          id="file-upload"
          disabled={isUploading}
        />
        
        <Button
          onClick={() => document.getElementById('file-upload')?.click()}
          className="bg-white/90 hover:bg-white text-black font-semibold px-8 py-3 rounded-lg"
          disabled={isUploading}
        >
          {isUploading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-black border-t-transparent mr-2"></div>
              Uploading...
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              Choose File
            </>
          )}
        </Button>
        
        {error && (
          <div className="mt-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function SpreadsheetPage() {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const router = useRouter()

  const [uploadedFileId, setUploadedFileId] = useState<string | null>(null)
  const plotRef = useRef<PlotlyChart>(null);

  const { 
    messages, 
    input, 
    handleInputChange, 
    handleSubmit, 
    isLoading, 
    error,
    clearMessages,
    uploadedFile,
    setUploadedFile
  } = useSpreadsheetChat({ streaming: true, fileId: uploadedFileId })

  const handleCopy = useCallback(async (message: SpreadsheetChatMessage) => {
    try {
      let textToCopy = message.content;
      const items: ClipboardItem[] = [new ClipboardItem({
        "text/plain": new Blob([textToCopy], { type: "text/plain" })
      })];

      await navigator.clipboard.write(items);
      alert('Content copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy: ', err);
      alert('Failed to copy content.');
    }
  }, [plotRef]);

  const handleFileUpload = async (file: File) => {
    setIsUploading(true)
    setUploadError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/spreadsheet/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to upload file')
      }

      const data = await response.json()
      setUploadedFile(file)
      setUploadedFileId(data.file_id) 
    } catch (error: any) {
      setUploadError(error.message || 'Failed to upload file. Please try again.')
    } finally {
      setIsUploading(false)
    }
  }

  const handleNewUpload = () => {
    setUploadedFile(null)
    setUploadedFileId(null)
    setUploadError(null)
    clearMessages()
  }

  return (
    <div className="flex h-screen w-full bg-transparent text-white font-sans">
      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        <header className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center space-x-3">
            <div className="flex items-center gap-3">
              <Image src="/landisgyr-logo-transparent.png" alt="Landis+Gyr" width={500} height={500} className="rounded-sm" />
              <h1 className="text-xl font-semibold">Spreadsheet Analysis</h1>
            </div>
            {uploadedFile && (
              <div className="flex items-center space-x-2 text-sm text-gray-400">
                <FileSpreadsheet className="h-4 w-4" />
                <span>{uploadedFile.name}</span>
              </div>
            )}
          </div>
          <Avatar></Avatar>
        </header>

        {!uploadedFile ? (
          <FileUpload 
            onFileUpload={handleFileUpload} 
            isUploading={isUploading} 
            error={uploadError}
          />
        ) : (
          <div className="flex-1 flex flex-col p-6 overflow-y-auto">
            {messages.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center">
                <div className="bg-white/10 p-4 rounded-full mb-4">
                  <Bot className="h-10 w-10" />
                </div>
                <h2 className="text-3xl font-bold">Ready to Analyze!</h2>
                <p className="text-4xl font-bold mt-2">Ask me anything about your data!</p>
                <p className="text-gray-400 mt-4">I can help you analyze your spreadsheet data</p>
              </div>
            ) : (
              <div className="flex justify-center">
                <div className="w-4/5 max-w-4xl space-y-6">
                  {messages.map((message: SpreadsheetChatMessage) => (
                    <div key={message.id} className={cn("flex gap-3", message.role === "user" ? "justify-end" : "justify-start")}>
                      {message.role !== "user" && message.content.trim() && (
                        <Avatar className="h-8 w-8 bg-white/10">
                          <AvatarFallback>
                            <Bot className="h-5 w-5" />
                          </AvatarFallback>
                        </Avatar>
                      )}
                      <div className="max-w-[75%] space-y-2">
                        {(message.content.trim() || message.plotlyPlot) && (
                          <div
                            className={cn(
                              "rounded-xl px-4 py-3 text-sm relative",
                              message.role === "user" ? "bg-green-600 text-white" : "bg-black/20",
                            )}
                          >
                            <div className="markdown-container">
                              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                                {message.content}
                              </ReactMarkdown>
                            </div>
                            {message.plotlyPlot && <PlotlyChart plotData={message.plotlyPlot} ref={plotRef} />}
                            {message.role !== "user" && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="mt-2 self-end text-white/50 hover:text-white"
                                onClick={() => handleCopy(message)}
                              >
                                <Clipboard className="h-4 w-4 mr-1" /> Copy
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                      {message.role === "user" && (
                        <Avatar className="h-8 w-8">
                          <AvatarFallback>
                            <User className="h-5 w-5" />
                          </AvatarFallback>
                        </Avatar>
                      )}
                    </div>
                  ))}
                  {isLoading && (
                    <div className="flex gap-3 justify-start">
                      <Avatar className="h-8 w-8 bg-white/10">
                        <AvatarFallback>
                          <Bot className="h-5 w-5" />
                        </AvatarFallback>
                      </Avatar>
                      <div className="bg-black/20 rounded-xl px-4 py-3 text-sm flex items-center">
                        <div className="h-2 w-2 bg-green-400 rounded-full animate-bounce [animation-delay:-0.3s] mr-1"></div>
                        <div className="h-2 w-2 bg-green-400 rounded-full animate-bounce [animation-delay:-0.15s] mr-1"></div>
                        <div className="h-2 w-2 bg-green-400 rounded-full animate-bounce"></div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {/* Error Display */}
            {error && (
              <div className="mx-6 mb-4 p-4 bg-red-500/20 border border-red-500/30 rounded-lg">
                <div className="flex items-center gap-2 text-red-400">
                  <HelpCircle className="h-4 w-4" />
                  <span className="text-sm font-medium">Error</span>
                </div>
                <p className="text-red-300 text-sm mt-1">{error}</p>
              </div>
            )}
          </div>
        )}
        
        {/* Chat Input - Only show if file is uploaded */}
        {uploadedFile && (
          <div className="px-6 pb-6 flex justify-center">
            <div className="chat-bar-wrapper w-4/5 max-w-4xl">
              <form onSubmit={handleSubmit} className="relative">
                <div className="flex items-center h-12 px-4 rounded-xl border border-white/25 chat-input-bar">
                  <div className="flex items-center justify-center w-8 h-8 cursor-pointer">
                    <Bot className="h-6 w-6 text-white stroke-[1.5]" />
                  </div>
                  <div className="w-px h-4 bg-white/40 mx-3"></div>
                  <Input
                    value={input}
                    onChange={handleInputChange}
                    placeholder="Ask me anything about your spreadsheet..."
                    className="flex-1 bg-transparent border-none text-white placeholder:text-white/85 placeholder:font-medium focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-auto text-base"
                  />
                  <div className="flex items-center space-x-3 ml-3">
                    <div className="flex items-center justify-center w-8 h-8 cursor-pointer">
                      <Mic className="h-6 w-6 text-white stroke-[1.5] hover:text-white/80 transition-colors" />
                    </div>
                    <Button
                      type="submit"
                      className="flex items-center justify-center w-8 h-8 bg-transparent hover:bg-transparent p-0 transition-colors"
                      disabled={isLoading}
                    >
                      <Send className="h-6 w-6 text-white stroke-[1.5] hover:text-white/80" />
                    </Button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>

      {/* Right Sidebar */}
      <aside className="hidden lg:flex flex-col w-80 p-6">
        <div className="bg-black/20 rounded-2xl flex-1 flex flex-col p-6">
          <div className="flex items-center space-x-2">
            <FileSpreadsheet className="h-6 w-6" />
            <h3 className="font-semibold">Spreadsheet Analysis</h3>
          </div>
          
          <hr className="my-4 border-white/10" />
          
          <div className="flex-1 space-y-4">
            <Button
              onClick={() => router.push('/')}
              className="w-full bg-gray-600 hover:bg-gray-700 text-white rounded-lg"
            >
              SQL Chat
            </Button>
            
            <Button
              className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
              disabled
            >
              Spreadsheet Chat
            </Button>
            
            {uploadedFile && (
              <Button
                onClick={handleNewUpload}
                className="w-full bg-white/90 hover:bg-white text-black font-bold rounded-lg"
              >
                <Plus className="mr-2 h-4 w-4" />
                New Analysis
              </Button>
            )}
          </div>
        </div>
      </aside>
    </div>
  )
}