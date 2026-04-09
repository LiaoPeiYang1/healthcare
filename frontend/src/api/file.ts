import { request } from '@/api/client'
import type { ApiEnvelope } from '@/types'

export const FILE_CHUNK_SIZE = 5 * 1024 * 1024

export async function checkFile(payload: {
  fileHash: string
  filename: string
  fileSize: number
  totalChunks: number
}) {
  const response = await request<ApiEnvelope<{ exists: boolean; file_id?: string | null }>>('/api/file/check', {
    method: 'POST',
    body: JSON.stringify({
      file_hash: payload.fileHash,
      filename: payload.filename,
      file_size: payload.fileSize,
      total_chunks: payload.totalChunks,
    }),
  })

  return {
    exists: response.data.exists,
    fileId: response.data.file_id ?? undefined,
  }
}

export async function uploadChunk(payload: {
  fileHash: string
  chunkIndex: number
  totalChunks: number
  chunk: Blob
  filename: string
}) {
  const form = new FormData()
  form.append('file_hash', payload.fileHash)
  form.append('chunk_index', String(payload.chunkIndex))
  form.append('total_chunks', String(payload.totalChunks))
  form.append('chunk', payload.chunk, payload.filename)

  return request<ApiEnvelope<{ success: boolean }>>('/api/file/chunk', {
    method: 'POST',
    body: form,
  })
}

export async function mergeChunks(payload: {
  fileHash: string
  filename: string
  totalChunks: number
  mimeType: string
}) {
  const response = await request<ApiEnvelope<{ file_id: string }>>('/api/file/merge', {
    method: 'POST',
    body: JSON.stringify({
      file_hash: payload.fileHash,
      filename: payload.filename,
      total_chunks: payload.totalChunks,
      mime_type: payload.mimeType,
    }),
  })
  return { fileId: response.data.file_id }
}
