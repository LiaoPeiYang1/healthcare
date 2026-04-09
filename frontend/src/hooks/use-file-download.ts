import { request } from '@/api/client'

export function useFileDownload() {
  const download = async (taskId: string, filename: string) => {
    const blob = await request<Blob>(`/api/translate/download/${taskId}`, {
      parseAs: 'blob',
    })

    const objectUrl = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    URL.revokeObjectURL(objectUrl)
  }

  return { download }
}
