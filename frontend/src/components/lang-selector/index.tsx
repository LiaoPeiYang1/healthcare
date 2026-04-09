import { Select, Typography } from 'antd'

import type { LanguageCode, SupportedLanguageCode } from '@/types'
import { formatLanguage, supportedLanguages } from '@/utils/format'

type LangSelectorProps = {
  sourceLang: LanguageCode
  targetLang: SupportedLanguageCode
  onSourceLangChange: (value: LanguageCode) => void
  onTargetLangChange: (value: SupportedLanguageCode) => void
  detectedLang?: string | null
  disabled?: boolean
}

export default function LangSelector({
  sourceLang,
  targetLang,
  onSourceLangChange,
  onTargetLangChange,
  detectedLang,
  disabled = false,
}: LangSelectorProps) {
  return (
    <div className="lang-selector-grid">
      <label>
        <Typography.Text>源语言</Typography.Text>
        <Select
          size="large"
          value={sourceLang}
          disabled={disabled}
          onChange={(value) => onSourceLangChange(value as LanguageCode)}
          options={[{ label: '自动检测', value: 'auto' }, ...supportedLanguages.map((item) => ({ label: item.label, value: item.code }))]}
        />
        {/* {sourceLang === 'auto' && detectedLang ? (
          <Typography.Text type="secondary">检测结果：{formatLanguage(detectedLang)}</Typography.Text>
        ) : null} */}
      </label>

      <label>
        <Typography.Text>目标语言</Typography.Text>
        <Select
          size="large"
          value={targetLang}
          disabled={disabled}
          onChange={(value) => onTargetLangChange(value as SupportedLanguageCode)}
          options={supportedLanguages.map((item) => ({ label: item.label, value: item.code }))}
        />
      </label>
    </div>
  )
}
