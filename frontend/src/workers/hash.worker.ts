import SparkMD5 from 'spark-md5'

self.onmessage = async (event: MessageEvent<{ file: File }>) => {
  try {
    const buffer = await event.data.file.arrayBuffer()
    const hash = SparkMD5.ArrayBuffer.hash(buffer)
    self.postMessage({ hash })
  } catch {
    self.postMessage({ error: '文件指纹计算失败' })
  }
}
