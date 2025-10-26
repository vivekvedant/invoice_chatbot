"use client"

import type React from "react"

import { useRef, useState } from "react"
import { Upload, Loader2, CheckCircle2, AlertCircle } from "lucide-react"

export function UploadSection({
  onUpload,
}: {
  onUpload: (
    file: File,
    setStatus: (s: { type: "success" | "error"; message: string } | null) => void,
    setBusy: (b: boolean) => void,
  ) => Promise<void>
}) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null)

  function handlePickFile() {
    inputRef.current?.click()
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.type !== "application/pdf") {
      setStatus({ type: "error", message: "Please select a PDF file" })
      return
    }
    onUpload(file, setStatus, setBusy)
    // reset input so selecting the same file again works
    e.currentTarget.value = ""
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6 mb-6 border border-blue-100">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
            <Upload className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-800">Upload New Invoice</h2>
            <p className="text-sm text-gray-600">Add PDF documents to your library</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {status && (
            <div
              className={`px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium ${
                status.type === "success"
                  ? "bg-green-50 text-green-700 border border-green-200"
                  : "bg-red-50 text-red-700 border border-red-200"
              }`}
            >
              {status.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
              {status.message}
            </div>
          )}

          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
            aria-label="Upload PDF"
          />
          <button
            disabled={busy}
            className="px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 disabled:opacity-50 transition-all shadow-lg hover:shadow-xl flex items-center gap-2 font-semibold"
            onClick={handlePickFile}
          >
            {busy ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                Upload PDF
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
