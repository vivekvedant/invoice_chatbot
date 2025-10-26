export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function formatUnixSeconds(ts: number) {
  // backend returns unix seconds
  return new Date(ts * 1000).toLocaleString()
}
