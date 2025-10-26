"use client";

import useSWR from "swr";
import { API_BASE_URL } from "@/lib/config";
import { UploadSection } from "./upload-section";
import { InvoicesTable } from "./invoices-table";
import { usePdfFiles } from "@/hooks/use-pdf-files";


export function InvoicesPage({
  onPdfCountChange,
}: {
  onPdfCountChange?: (count: number) => void;
}) {
  const { pdfs, isLoading, mutate } = usePdfFiles();

  // keep sidebar count in sync
  if (onPdfCountChange) {
    // avoid extra renders: only update when value differs
    Promise.resolve().then(() => onPdfCountChange(pdfs.length));
  }

  async function handleUpload(
    file: File,
    setStatus: (
      s: { type: "success" | "error"; message: string } | null
    ) => void,
    setBusy: (b: boolean) => void
  ) {
    if (!file) return;
    setBusy(true);
    setStatus(null);

    try {
      const presignedResponse = await fetch(
        `${API_BASE_URL}/generate-presigned-url/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file_name: file.name }),
        }
      );
      if (!presignedResponse.ok) throw new Error("Failed to get presigned URL");
      const { presigned_url } = await presignedResponse.json();

      const uploadResponse = await fetch(presigned_url, {
        method: "PUT",
        headers: { "Content-Type": "application/pdf" },
        body: file,
      });
      if (!uploadResponse.ok) throw new Error("Failed to upload file to S3");

      setStatus({ type: "success", message: "Invoice uploaded successfully!" });
      await mutate();
      setTimeout(() => setStatus(null), 2000);
    } catch (err: any) {
      setStatus({ type: "error", message: err?.message || "Upload failed" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="flex-1 overflow-y-auto p-8 bg-gradient-to-b from-blue-50/30 to-white"
      aria-label="Invoices"
    >
      <div className="max-w-6xl mx-auto">
        <UploadSection onUpload={handleUpload} />
        <InvoicesTable
          pdfs={pdfs}
          loading={isLoading && pdfs.length === 0}
          onRefresh={() => mutate()}
        />
      </div>
    </section>
  );
}
