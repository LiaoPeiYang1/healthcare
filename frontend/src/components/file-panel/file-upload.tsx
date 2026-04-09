import { UploadCloud } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'

import { formatFileSize } from '@/utils/format'

type FileUploadProps = {
  disabled: boolean
  onFileSelected: (file: File) => void
}

const MAX_FILE_SIZE = 100 * 1024 * 1024

export default function FileUpload({ disabled, onFileSelected }: FileUploadProps) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    disabled,
    multiple: false,
    maxSize: MAX_FILE_SIZE,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    onDropAccepted(files) {
      const file = files[0]
      if (file) onFileSelected(file)
    },
    onDropRejected(rejections) {
      const firstError = rejections[0]?.errors[0]
      if (firstError?.code === 'file-too-large') {
        toast.error('文件大小不能超过 100MB')
        return
      }
      toast.error('仅支持 .docx 和 .pdf 文件')
    },
  })

  return (
    <div {...getRootProps()} className={`upload-dropzone ${isDragActive ? 'is-active' : ''} ${disabled ? 'is-disabled' : ''}`}>
      <input {...getInputProps()} />
      <div className="upload-dropzone-icon">
        <UploadCloud size={28} />
      </div>
      <div className="upload-dropzone-copy">
        <strong>点击或拖拽上传</strong>
        <p>支持 .docx 和文本型 .pdf，单文件最大 {formatFileSize(MAX_FILE_SIZE)}。</p>
        <span>上传后自动开始翻译，完成后直接展示文档对照预览。</span>
      </div>
    </div>
  )
}
