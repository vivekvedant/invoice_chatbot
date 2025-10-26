"use client"

import { Brain, FileText, Sparkles, X } from "lucide-react"
import { cn } from "@/lib/utils"

type TabKey = "chat" | "invoices"

export function Sidebar({
  open,
  onClose,
  activeTab,
  onSelectTab,
  pdfCount = 0,
}: {
  open: boolean
  onClose: () => void
  activeTab: TabKey
  onSelectTab: (tab: TabKey) => void
  pdfCount?: number
}) {
  return (
    <aside
      className={cn(
        "fixed lg:relative z-30 w-80 h-full bg-white shadow-2xl transition-transform duration-300 ease-in-out flex flex-col",
        open ? "translate-x-0" : "-translate-x-full",
        "lg:translate-x-0",
      )}
    >
      {/* Header */}
      <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-indigo-50 to-purple-50">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="relative">
              <Brain className="w-8 h-8 text-indigo-600" />
              <Sparkles className="w-3 h-3 text-yellow-500 absolute -top-1 -right-1" />
            </div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              Invoice AI
            </h1>
          </div>
          <button onClick={onClose} className="lg:hidden text-gray-500 hover:text-gray-700" aria-label="Close sidebar">
            <X className="w-6 h-6" />
          </button>
        </div>
        <p className="text-xs text-gray-600">Navigate between features</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-4 space-y-3 overflow-y-auto" aria-label="Primary">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">Main Features</div>

        <button
          onClick={() => onSelectTab("chat")}
          className={cn(
            "w-full px-4 py-4 rounded-xl font-semibold transition-all flex items-center gap-3",
            activeTab === "chat"
              ? "bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg"
              : "text-gray-700 hover:bg-gray-100 border border-gray-200",
          )}
          aria-current={activeTab === "chat" ? "page" : undefined}
        >
          <Brain className="w-5 h-5" />
          <div className="flex-1 text-left">
            <div>Chat & Analyze</div>
            <div className="text-xs opacity-80 font-normal">Ask questions</div>
          </div>
        </button>

        <button
          onClick={() => onSelectTab("invoices")}
          className={cn(
            "w-full px-4 py-4 rounded-xl font-semibold transition-all flex items-center gap-3",
            activeTab === "invoices"
              ? "bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg"
              : "text-gray-700 hover:bg-gray-100 border border-gray-200",
          )}
          aria-current={activeTab === "invoices" ? "page" : undefined}
        >
          <FileText className="w-5 h-5" />
          <div className="flex-1 text-left">
            <div>Invoices</div>
            <div className="text-xs opacity-80 font-normal">{pdfCount} documents</div>
          </div>
        </button>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">AI-powered invoice intelligence</p>
      </div>
    </aside>
  )
}
