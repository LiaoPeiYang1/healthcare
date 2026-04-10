import { Alert, Button, Select, Typography } from 'antd'
import { ArrowRight, SendHorizonal } from 'lucide-react'
import { toast } from 'sonner'

import TextInput from '@/components/text-panel/text-input'
import TextResult from '@/components/text-panel/text-result'
import { useTextTranslation } from '@/hooks/use-text-translation'
import { supportedLanguages } from '@/utils/format'

export default function TextPanel() {
  const {
    sourceText,
    translatedText,
    targetLang,
    status,
    error,
    canSubmit,
    setSourceText,
    setTargetLanguage,
    submit,
    retry,
  } = useTextTranslation()

  const showWorkspaceLayout = status !== 'idle'

  const handleSubmit = async () => {
    try {
      await submit()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '文本翻译失败')
    }
  }

  return (
    <div className={`panel-block text-panel-block ${showWorkspaceLayout ? 'is-workspace' : 'is-compose'}`}>
      <div className={`text-toolbar ${showWorkspaceLayout ? 'is-workspace' : 'is-compose'}`}>
        <div className="text-toolbar-fixed" aria-label="源语言固定为自动检测">
          <Typography.Text>自动检测</Typography.Text>
        </div>
        <div className="text-toolbar-arrow">
          <ArrowRight size={18} />
        </div>
        <Select
          size="large"
          value={targetLang}
          className="text-toolbar-select"
          onChange={setTargetLanguage}
          options={supportedLanguages.map((item) => ({ label: item.label, value: item.code }))}
        />
      </div>

      {/* {sourceLang === 'auto' && detectedLang ? (
        <div className={`text-detected-note ${showWorkspaceLayout ? 'is-left' : 'is-center'}`}>
          <Typography.Text type="secondary">检测结果：{supportedLanguages.find((item) => item.code === detectedLang)?.label ?? detectedLang}</Typography.Text>
        </div>
      ) : null} */}

      {showWorkspaceLayout ? (
        <div className="text-workspace-grid">
          <section className="text-workspace-pane text-workspace-pane-source">
            <div className="text-pane-header">
              <div className="text-pane-label">
                <span className="pane-dot" />
                <Typography.Text strong>原文内容</Typography.Text>
              </div>
              <span className="text-pane-meta">{sourceText.length} 字符</span>
            </div>

            <div className="text-pane-body text-input-shell is-workspace">
              <TextInput value={sourceText} onChange={setSourceText} disabled={status === 'loading'} />
            </div>

            {error ? (
              <div className="surface-alert-stack">
                {error ? <Alert type="error" message={error} showIcon /> : null}
              </div>
            ) : null}

            <div className="text-pane-footer">
              {status === 'failed' ? (
                <Button size="large" onClick={() => void retry()}>
                  重试
                </Button>
              ) : null}
              <Button
                type="primary"
                size="large"
                icon={<SendHorizonal size={16} />}
                onClick={handleSubmit}
                disabled={!canSubmit}
                loading={status === 'loading'}
                className="compose-submit"
              >
                开始翻译
              </Button>
            </div>
          </section>

          <section className="text-workspace-pane text-workspace-pane-result">
            <TextResult translatedText={translatedText} status={status} />
          </section>
        </div>
      ) : (
        <div className="mode-panel-center">
          <div className="mode-compose-shell text-compose-shell">
            <div className="text-input-shell is-compose">
              <TextInput value={sourceText} onChange={setSourceText} />
            </div>

            {error ? (
              <div className="surface-alert-stack">
                {error ? <Alert type="error" message={error} showIcon /> : null}
              </div>
            ) : null}

            <div className="compose-footer">
              <Typography.Text type="secondary">{sourceText.length} 字符</Typography.Text>
              <div className="compose-actions">
                <Button
                  type="primary"
                  size="large"
                  icon={<SendHorizonal size={16} />}
                  onClick={handleSubmit}
                  disabled={!canSubmit}
                  className="compose-submit"
                >
                  开始翻译
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
