import useSWR from "swr";
import { API_BASE_URL } from "@/lib/config";

export type PdfFile = { name: string; size: number; last_modified: number };

const fetcher = (url: string) =>
  fetch(url).then((r) => {
    if (!r.ok) throw new Error("Failed to load");
    return r.json();
  });

export function usePdfFiles() {
  const { data, isLoading, mutate } = useSWR<{ pdf_files: PdfFile[] }>(
    `${API_BASE_URL}/list-pdfs/`,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 10000, // prevent repeat calls within 10s
    }
  );
  return { pdfs: data?.pdf_files ?? [], isLoading, mutate };
}
