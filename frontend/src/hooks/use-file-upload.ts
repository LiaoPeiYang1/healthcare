import { useCallback } from 'react'

import { checkFile, FILE_CHUNK_SIZE, mergeChunks, uploadChunk } from '@/api/file'
import { useFileTranslateStore } from '@/store/file-translate'

function calculateFileHash(file: File) {
  return new Promise<string>((resolve, reject) => {
    const worker = new Worker(new URL('../workers/hash.worker.ts', import.meta.url), { type: 'module' })
    worker.onmessage = (event: MessageEvent<{ hash?: string; error?: string }>) => {
      worker.terminate()
      if (event.data.error) {
        reject(new Error(event.data.error))
        return
      }
      resolve(event.data.hash ?? '')
    }
    worker.onerror = () => {
      worker.terminate()
      reject(new Error('文件指纹计算失败'))
    }
    worker.postMessage({ file })
  })
}

export function useFileUpload() {
  const updateTask = useFileTranslateStore((state) => state.updateTask)

  const uploadFile = useCallback(
    async (file: File) => {
      const totalChunks = Math.max(1, Math.ceil(file.size / FILE_CHUNK_SIZE))
      updateTask({ status: 'hashing', uploadProgress: 0, error: undefined })

      const fileHash = await calculateFileHash(file)
      const checked = await checkFile({
        fileHash,
        filename: file.name,
        fileSize: file.size,
        totalChunks,
      })

      if (checked.exists && checked.fileId) {
        return {
          fileId: checked.fileId,
          fileHash,
          totalChunks,
        }
      }

      updateTask({ status: 'uploading', uploadProgress: 0 })

      for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex += 1) {
        const start = chunkIndex * FILE_CHUNK_SIZE
        const end = Math.min(file.size, start + FILE_CHUNK_SIZE)
        const chunk = file.slice(start, end)

        await uploadChunk({
          fileHash,
          chunkIndex,
          totalChunks,
          chunk,
          filename: file.name,
        })

        updateTask({ uploadProgress: Math.round(((chunkIndex + 1) / totalChunks) * 100) })
      }

      const merged = await mergeChunks({
        fileHash,
        filename: file.name,
        totalChunks,
        mimeType: file.type || 'application/octet-stream',
      })

      return {
        fileId: merged.fileId,
        fileHash,
        totalChunks,
      }
    },
    [updateTask],
  )

  return { uploadFile }
}
