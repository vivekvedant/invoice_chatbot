"use client";

import React, { useState } from "react";
import {
  FileText,
  Loader2,
  Trash2,
  X,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { API_BASE_URL } from "../../lib/config";

type PdfFile = {
  file_name: string;
  status: "pending" | "indexing" | "completed" | "error";
  last_updated: string;
};

interface InvoicesTableProps {
  pdfs: PdfFile[];
  loading: boolean;
  onRefresh: () => void;
  onSelectDocument?: (documentNumber: number) => void;
  onDelete?: (fileName: string, index: number) => void;
}

export function InvoicesTable({
  pdfs,
  loading,
  onRefresh,
  onSelectDocument,
  onDelete,
}: InvoicesTableProps) {
  const [loadingFile, setLoadingFile] = useState<string | null>(null);
  const [deletingFile, setDeletingFile] = useState<string | null>(null);
  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    fileName: string;
    index: number;
  }>({
    isOpen: false,
    fileName: "",
    index: -1,
  });
  const [errorModal, setErrorModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
  }>({
    isOpen: false,
    title: "",
    message: "",
  });

  const showError = (title: string, message: string) => {
    setErrorModal({
      isOpen: true,
      title,
      message,
    });
  };

  const closeErrorModal = () => {
    setErrorModal({
      isOpen: false,
      title: "",
      message: "",
    });
  };

  const handleFileClick = async (fileName: string) => {
    try {
      setLoadingFile(fileName);

      const response = await fetch(
        `${API_BASE_URL}/get_file_link?file_name=${encodeURIComponent(
          fileName
        )}`,
        {
          method: "GET",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to get file link");
      }

      const data = await response.json();

      if (data.download_url) {
        window.open(data.download_url, "_blank");
      } else {
        console.error("No URL returned from API");
        showError(
          "File Not Found",
          "Failed to retrieve the file link. Please try again."
        );
      }
    } catch (error) {
      console.error("Error fetching file link:", error);
      showError(
        "Connection Error",
        "Unable to open the file. Please check your connection and try again."
      );
    } finally {
      setLoadingFile(null);
    }
  };

  const openDeleteModal = (fileName: string, index: number) => {
    setDeleteModal({
      isOpen: true,
      fileName,
      index,
    });
  };

  const closeDeleteModal = () => {
    setDeleteModal({
      isOpen: false,
      fileName: "",
      index: -1,
    });
  };

  const handleDeleteConfirm = async () => {
    const { fileName, index } = deleteModal;

    try {
      setDeletingFile(fileName);
      closeDeleteModal();

      const response = await fetch(`${API_BASE_URL}/delete_file`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ file_name: fileName }),
      });

      if (!response.ok) {
        throw new Error("Failed to delete file");
      }

      const data = await response.json();

      if (data.success) {
        onDelete?.(fileName, index);
        onRefresh();
      } else {
        console.error("Delete failed:", data.message);
        showError(
          "Delete Failed",
          data.message || "Unable to delete the file. Please try again."
        );
      }
    } catch (error) {
      console.error("Error deleting file:", error);
      showError(
        "Delete Error",
        "An error occurred while deleting the file. Please try again."
      );
    } finally {
      setDeletingFile(null);
    }
  };

  return (
    <>
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
            <p className="text-gray-500 text-sm">
              Click "Upload PDF" to add your first invoice
            </p>
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
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Last Updated
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {pdfs.map((pdf, idx) => (
                  <tr
                    key={idx}
                    className="hover:bg-blue-50/50 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                          <FileText className="w-5 h-5 text-white" />
                        </div>
                        <button
                          onClick={() => handleFileClick(pdf.file_name)}
                          className="text-gray-800 font-medium hover:text-blue-600 transition-colors text-left cursor-pointer flex items-center gap-2"
                          disabled={loadingFile === pdf.file_name}
                          title="Open PDF in new tab"
                        >
                          {loadingFile === pdf.file_name && (
                            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                          )}
                          {pdf.file_name}
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                          pdf.status === "completed"
                            ? "bg-green-100 text-green-800"
                            : pdf.status === "indexing"
                            ? "bg-blue-100 text-blue-800"
                            : pdf.status === "pending"
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {pdf.status === "indexing" && (
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                        )}
                        {pdf.status.charAt(0).toUpperCase() +
                          pdf.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-600">
                      {new Date(
                        parseInt(pdf.last_updated) * 1000
                      ).toLocaleString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => openDeleteModal(pdf.file_name, idx)}
                        disabled={deletingFile === pdf.file_name}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                        title="Delete invoice"
                      >
                        {deletingFile === pdf.file_name ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-red-600" />
                </div>
                <h3 className="text-xl font-bold text-gray-900">
                  Delete Invoice
                </h3>
              </div>
              <button
                onClick={closeDeleteModal}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              <p className="text-gray-600 mb-2">
                Are you sure you want to delete this invoice?
              </p>
              <p className="text-sm font-medium text-gray-900 bg-gray-50 p-3 rounded-lg border border-gray-200">
                {deleteModal.fileName}
              </p>
              <p className="text-sm text-red-600 mt-4">
                This action cannot be undone.
              </p>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center gap-3 p-6 bg-gray-50 rounded-b-2xl">
              <button
                onClick={closeDeleteModal}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Modal */}
      {errorModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                  <XCircle className="w-6 h-6 text-red-600" />
                </div>
                <h3 className="text-xl font-bold text-gray-900">
                  {errorModal.title}
                </h3>
              </div>
              <button
                onClick={closeErrorModal}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              <p className="text-gray-600">{errorModal.message}</p>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center gap-3 p-6 bg-gray-50 rounded-b-2xl">
              <button
                onClick={closeErrorModal}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
