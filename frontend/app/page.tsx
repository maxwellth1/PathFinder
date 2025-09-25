"use client"
import { useJewelryChat } from "@/hooks/use-jewelry-chat"
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
  FileSpreadsheet,
  Database,
  Clipboard,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { ChatMessage } from "@/hooks/use-jewelry-chat"
import { useState, useCallback } from "react"
import { useRouter } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import '@/styles/markdown.css'
import Image from 'next/image'

const navItems = [
  { icon: Home, label: "Home" },
  { icon: LayoutGrid, label: "Dashboard" },
  { icon: Gem, label: "Jewellery", active: true },
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

export default function ChatPage() {
  const { messages, input, handleInputChange, handleSubmit, isLoading, error, clearMessages } = useJewelryChat({
    streaming: true // Enable streaming for token-by-token responses
  })
  
  const router = useRouter()

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      alert('Content copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy: ', err);
      alert('Failed to copy content.');
    }
  }, []);
  return (
    <div className="flex h-screen w-full bg-transparent text-white font-sans">
      {/* Main Chat Panel */}
      <main className="flex-1 flex flex-col">
        <header className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <Image src="/landisgyr-logo-transparent.png" alt="Landis+Gyr" width={120} height={120} className="rounded-sm w-[84px] h-[84px] md:w-[96px] md:h-[96px] lg:w-[120px] lg:h-[120px]" />
            <h1 className="text-xl font-semibold">Path Finder</h1>
          </div>
          <Avatar>
          </Avatar>
        </header>

        <div className="flex-1 flex flex-col p-6 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center">
              <div className="bg-white/10 p-4 rounded-full mb-4">
                <Bot className="h-10 w-10" />
              </div>
              <h2 className="text-3xl font-bold">Hello, Boss!</h2>
              <p className="text-4xl font-bold mt-2">I am ready to assist you!</p>
              <p className="text-gray-400 mt-4">Ask me anything, what's are on your mind?</p>
            </div>
          ) : (
            <div className="flex justify-center">
              <div className="w-4/5 max-w-4xl space-y-6">
                {messages.map((message: ChatMessage) => (
                  <div key={message.id} className={cn("flex gap-3", message.role === "user" ? "justify-end" : "justify-start")}>
                    {message.role !== "user" && message.content.trim() && (
                      <Avatar className="h-8 w-8 bg-black">
                        <AvatarFallback>
                          <Bot className="h-5 w-5" />
                        </AvatarFallback>
                      </Avatar>
                    )}
                    <div className="max-w-[90%] space-y-2">
                      {message.content.trim() && (
                        <div
                          className={cn(
                            "rounded-xl px-4 py-3 text-sm",
                            message.role === "user" ? "bg-green-600 text-white" : "bg-transparent",
                          )}
                        >
                          <div className="markdown-container">
                            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                              {message.content}
                            </ReactMarkdown>
                          </div>
                          {message.role !== "user" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="absolute top-2 right-2 text-white/50 hover:text-white"
                              onClick={() => handleCopy(message.content)}
                            >
                              <Clipboard className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                    {message.role === "user" && (
                      <Avatar className="h-8 w-8 bg-black">
                        <AvatarFallback>
                          <User className="h-5 w-5" />
                        </AvatarFallback>
                      </Avatar>
                    )}
                  </div>
                ))}
                {isLoading && (
                  <div className="flex gap-3 justify-start">
                    <Avatar className="h-8 w-8 bg-black">
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
                  placeholder="Ask me anything"
                  className="flex-1 bg-transparent border-none text-white placeholder:text-white/85 placeholder:font-medium focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-auto text-base"
                />
                <div className="flex items-center space-x-3 ml-3">
                  <div className="flex items-center justify-center w-8 h-8 cursor-pointer">
                    <Mic className="h-6 w-6 text-white stroke-[1.5] hover:text-white/80 transition-colors" />
                  </div>
                  <Button
                    type="submit"
                    className="flex items-center justify-center w-8 h-8 bg-transparent hover:bg-transparent p-0 transition-colors"
                  >
                    <Send className="h-6 w-6 text-white stroke-[1.5] hover:text-white/80" />
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </main>

      {/* Right Sidebar */}
      <aside className="hidden lg:flex flex-col w-80 p-6">
        <div className="bg-black/20 rounded-2xl flex-1 flex flex-col p-6">
          
          
          {/* Navigation Buttons */}
          <div className="mt-4 space-y-2">
            <Button 
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg"
              disabled
            >
              <Database className="mr-2 h-4 w-4" />
              SQL Chat
            </Button>
            <Button 
              className="w-full bg-gray-600 hover:bg-gray-700 text-white rounded-lg"
              onClick={() => router.push('/spreadsheet')}
            >
              <FileSpreadsheet className="mr-2 h-4 w-4" />
              Spreadsheet Chat
            </Button>
          </div>
          
          <Button 
            className="w-full mt-4 bg-white/90 hover:bg-white text-black font-bold rounded-lg"
            onClick={clearMessages}
          >
            <Plus className="mr-2 h-4 w-4" />
            New Chat
          </Button>
        </div>
      </aside>
    </div>
  )
}
