"use client"

import { Brain, Menu } from "lucide-react"

export function MobileHeader({ onOpenMenu }: { onOpenMenu: () => void }) {
  return (
    <header className="lg:hidden bg-white border-b border-gray-200 p-4 flex items-center gap-3 shadow-md">
      <button onClick={onOpenMenu} className="text-gray-700 hover:bg-gray-100 p-2 rounded-lg" aria-label="Open menu">
        <Menu className="w-6 h-6" />
      </button>
      <div className="flex items-center gap-2">
        <Brain className="w-6 h-6 text-indigo-600" />
        <h1 className="text-lg font-bold text-gray-800">Invoice AI</h1>
      </div>
    </header>
  )
}
