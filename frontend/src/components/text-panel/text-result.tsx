import { Button, Empty, Typography } from 'antd'
import { Copy } from 'lucide-react'
import { toast } from 'sonner'

type TextResultProps = {
  translatedText: string
  status: 'idle' | 'loading' | 'success' | 'failed'
}

export default function TextResult({ translatedText, status }: TextResultProps) {
  const handleCopy = async () => {
    if (!translatedText) return
    await navigator.clipboard.writeText(translatedText)
    toast.success('译文已复制')
  }

  if (status === 'loading' && !translatedText) {
    return (
      <div className="text-result-pane is-loading">
        <Typography.Text type="secondary">翻译中...</Typography.Text>
      </div>
    )
  }

  return (
    <div className="text-result-pane">
      <div className="text-pane-header">
        <div className="text-pane-label is-result">
          <span className="pane-dot is-result" />
          <Typography.Text strong>翻译结果</Typography.Text>
        </div>
        <div className="text-result-actions">
          {status === 'success' ? <span className="result-badge">已对齐</span> : null}
          {status === 'success' ? (
            <Button type="text" icon={<Copy size={16} />} onClick={handleCopy}>
              复制
            </Button>
          ) : null}
        </div>
      </div>
      {translatedText ? (
        <pre className="text-result-content">{translatedText}</pre>
      ) : (
        <Empty description="这里会展示翻译结果" />
      )}
    </div>
  )
}
