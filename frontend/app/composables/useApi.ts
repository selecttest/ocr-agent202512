/**
 * API 服務層 - 連接後端 OCR API
 */

// API 基礎 URL 會在 useApi() 中從 runtimeConfig 讀取

// ==================== 類型定義 ====================

/** OCR 區塊 */
export interface OCRBlock {
  id: string
  type: string
  page: number
  region: string
  content: string
  confidence?: number
}

/** 文件列表項目 */
export interface DocumentItem {
  id: string
  filename: string
  detected_type: string
  language: string
  total_pages: number
  upload_time: string
}

/** OCR 上傳回應 */
export interface OCRResponse {
  success: boolean
  document_id?: string
  total_pages: number
  detected_type: string
  language: string
  blocks: OCRBlock[]
  full_text: string
  key_value_pairs: Array<{ key: string; value: string; page: number }>
  tables: Array<{ id: string; page: number; summary: string }>
  images_summary?: {
    total_count: number
    items: Array<{ id: string; type: string; page: number; description: string }>
  }
  processing_time?: {
    total_seconds: number
    total_formatted: string
    batch_count?: number
  }
  error?: string
}

/** 文件詳情 */
export interface DocumentDetail {
  document: DocumentItem & {
    summary: string
    processing_time_seconds?: number
    metadata: Record<string, unknown>
  }
  blocks: Array<OCRBlock & { block_id: string; block_type: string }>
  key_values: Array<{ id: string; key: string; value: string; page: number }>
  images: Array<{ id: string; image_type: string; page: number; region: string; description: string }>
}

/** RAG 問答請求 */
export interface AskRequest {
  question: string
  top_k?: number
  document_ids?: string[]
}

/** RAG 問答回應 */
export interface AskResponse {
  answer: string
  sources: Array<{
    filename: string
    page: number
    content: string
    similarity?: number
  }>
}

/** 健康檢查回應 */
export interface HealthResponse {
  status: string
  project_id: string
  location: string
  version: string
}

/** 刪除回應 */
export interface DeleteResponse {
  success: boolean
  message: string
}

/** 批次刪除回應 */
export interface BatchDeleteResponse {
  deleted: number
  failed: number
  deleted_ids: string[]
}

/** OCR 處理進度 */
export interface OCRProgress {
  type: 'start' | 'info' | 'progress' | 'status' | 'complete' | 'error'
  // start
  total_pages?: number
  filename?: string
  // info
  batch_size?: number
  total_batches?: number
  // progress
  current_page?: number
  end_page?: number
  batch?: number
  percent?: number
  status?: string
  // status
  message?: string
  // complete
  result?: OCRResponse
  // error
  error?: string
}

// ==================== API Composable ====================

export const useApi = () => {
  // 從 runtimeConfig 讀取 API URL
  const config = useRuntimeConfig()
  const API_BASE_URL = config.public.apiBase || 'http://localhost:8000'
  
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * 健康檢查
   */
  const healthCheck = async (): Promise<HealthResponse | null> => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`)
      if (!response.ok) return null
      return await response.json()
    } catch {
      return null
    }
  }

  /**
   * 上傳 PDF 進行 OCR
   */
  const uploadPDF = async (file: File, saveToDb = true): Promise<OCRResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(
        `${API_BASE_URL}/ocr/upload?save_to_db=${saveToDb}`,
        {
          method: 'POST',
          body: formData
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '上傳失敗')
      }

      return await response.json()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '上傳失敗'
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 上傳 PDF 進行 OCR（含進度追蹤）
   * @param file 要上傳的 PDF 檔案
   * @param saveToDb 是否儲存到資料庫
   * @param onProgress 進度回調函數
   * @param abortSignal 可選的 AbortSignal 用於取消請求
   */
  const uploadPDFWithProgress = async (
    file: File,
    saveToDb = true,
    onProgress: (progress: OCRProgress) => void,
    abortSignal?: AbortSignal
  ): Promise<OCRResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(
        `${API_BASE_URL}/ocr/upload-stream?save_to_db=${saveToDb}`,
        {
          method: 'POST',
          body: formData,
          signal: abortSignal
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '上傳失敗')
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('無法讀取串流')
      }

      const decoder = new TextDecoder()
      let buffer = ''
      let result: OCRResponse | null = null

      // 監聽取消信號
      if (abortSignal) {
        abortSignal.addEventListener('abort', () => {
          reader.cancel()
        })
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // 檢查是否已取消
        if (abortSignal?.aborted) {
          throw new Error('已取消辨識')
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)) as OCRProgress
              onProgress(data)

              if (data.type === 'complete' && data.result) {
                result = data.result
              } else if (data.type === 'error') {
                throw new Error(data.message || '處理失敗')
              }
            } catch (parseError) {
              console.error('解析進度失敗:', parseError)
            }
          }
        }
      }

      return result
    } catch (e) {
      // 如果是取消導致的錯誤，不顯示錯誤訊息
      if (e instanceof Error && (e.name === 'AbortError' || e.message === '已取消辨識')) {
        error.value = null
      } else {
        error.value = e instanceof Error ? e.message : '上傳失敗'
      }
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 取得文件列表
   */
  const getDocuments = async (limit = 20): Promise<DocumentItem[]> => {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/documents?limit=${limit}`)

      if (!response.ok) {
        throw new Error('取得文件列表失敗')
      }

      const data = await response.json()
      return data.documents || []
    } catch (e) {
      error.value = e instanceof Error ? e.message : '取得文件列表失敗'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * 取得文件詳情
   */
  const getDocument = async (docId: string): Promise<DocumentDetail | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/documents/${docId}`)

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('文件不存在')
        }
        throw new Error('取得文件詳情失敗')
      }

      return await response.json()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '取得文件詳情失敗'
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * RAG 問答
   */
  const askQuestion = async (question: string, topK = 5): Promise<AskResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question, top_k: topK })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '問答失敗')
      }

      return await response.json()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '問答失敗'
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * RAG 問答（指定文件）
   */
  const askQuestionWithDocs = async (
    question: string,
    documentIds: string[],
    topK = 5
  ): Promise<AskResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          question,
          top_k: topK,
          document_ids: documentIds
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '問答失敗')
      }

      return await response.json()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '問答失敗'
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 刪除單一文件
   */
  const deleteDocument = async (docId: string): Promise<DeleteResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/documents/${docId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '刪除失敗')
      }

      return await response.json()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '刪除失敗'
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 批次刪除多個文件
   */
  const deleteDocuments = async (docIds: string[]): Promise<BatchDeleteResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/documents/batch-delete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ document_ids: docIds })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '批次刪除失敗')
      }

      return await response.json()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '批次刪除失敗'
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    // 狀態
    loading: readonly(loading),
    error: readonly(error),
    // 方法
    healthCheck,
    uploadPDF,
    uploadPDFWithProgress,
    getDocuments,
    getDocument,
    deleteDocument,
    deleteDocuments,
    askQuestion,
    askQuestionWithDocs
  }
}

