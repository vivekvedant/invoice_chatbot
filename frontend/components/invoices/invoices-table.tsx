"use client"

import { FileText, Loader2 } from "lucide-react"
import { formatBytes, formatUnixSeconds } from "@/lib/format"

type PdfFile = { name: string; size: number; last_modified: number }

export function InvoicesTable({
  pdfs,
  loading,
  onRefresh,
}: {
  pdfs: PdfFile[]
  loading: boolean
  onRefresh: () => void
}) {
  return (
    <div className="bg-white rounded-2xl shadow-lg overflow-hidden border border-gray-200">
      <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-800">Invoice Library</h3>
          <button
            onClick={onRefresh}
            className="px-4 py-2 text-sm bg-white text-gray-700 rounded-lg hover:bg-gray-50 transition-colors border border-gray-300 font-medium"
          >
            Refresh
          </button>
        </div>
      </div>

      {loading && pdfs.length === 0 ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      ) : pdfs.length === 0 ? (
        <div className="text-center py-16 px-6">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <FileText className="w-10 h-10 text-gray-400" />
          </div>
          <p className="text-gray-600 font-medium mb-1">No invoices yet</p>
          <p className="text-gray-500 text-sm">Click "Upload PDF" to add your first invoice</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  File Name
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Size
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Date Added
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {pdfs.map((pdf, idx) => (
                <tr key={idx} className="hover:bg-blue-50/50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                        <FileText className="w-5 h-5 text-white" />
                      </div>
                      <span className="text-gray-800 font-medium">{pdf.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-600">{formatBytes(pdf.size)}</td>
                  <td className="px-6 py-4 text-gray-600">{formatUnixSeconds(pdf.last_modified)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
