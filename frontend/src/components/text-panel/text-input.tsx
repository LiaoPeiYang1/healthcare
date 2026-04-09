import { Input } from 'antd'

const { TextArea } = Input

type TextInputProps = {
  value: string
  disabled?: boolean
  onChange: (value: string) => void
}

export default function TextInput({ value, disabled = false, onChange }: TextInputProps) {
  return (
    <TextArea
      value={value}
      rows={10}
      maxLength={5000}
      disabled={disabled}
      showCount
      placeholder="输入医药文本，例如：随机对照试验的主要终点为总生存期。"
      onChange={(event) => onChange(event.target.value)}
    />
  )
}
