import { Button } from 'antd'
import { Download } from 'lucide-react'
import { toast } from 'sonner'

import { useFileDownload } from '@/hooks/use-file-download'
import { buildDownloadFilename } from '@/utils/format'

type DownloadBarProps = {
  taskId?: string
  title: string
  targetLang: string
}

export default function DownloadBar({ taskId, title, targetLang }: DownloadBarProps) {
  const { download } = useFileDownload()

  const handleDownload = async () => {
    if (!taskId) return
    try {
      await download(taskId, buildDownloadFilename(title, targetLang))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '下载失败，请重试')
    }
  }

  return (
    <div className="download-bar">
      <Button type="primary" icon={<Download size={16} />} disabled={!taskId} onClick={() => void handleDownload()}>
        下载纯译文 PDF
      </Button>
    </div>
  )
}
