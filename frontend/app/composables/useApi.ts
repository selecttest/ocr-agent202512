/**
 * API 服務層 - 連接後端 OCR API
 */

// API 基礎 URL（可透過環境變數設定）
const API_BASE_URL = 'http://localhost:8000'

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

// ==================== API Composable ====================

export const useApi = () => {
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

  return {
    // 狀態
    loading: readonly(loading),
    error: readonly(error),
    // 方法
    healthCheck,
    uploadPDF,
    getDocuments,
    getDocument,
    askQuestion
  }
}

