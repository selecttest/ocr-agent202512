<script setup lang="ts">
import type { OCRResponse, OCRProgress } from '~/composables/useApi'

const { uploadPDFWithProgress, loading, error } = useApi()

// 狀態
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const uploadResult = ref<OCRResponse | null>(null)
const saveToDb = ref(true)
const fileInputRef = ref<HTMLInputElement | null>(null)

// 進度狀態
const progress = ref({
  totalPages: 0,
  currentPage: 0,
  endPage: 0,
  percent: 0,
  batch: 0,
  totalBatches: 0,
  status: '',
  message: ''
})

// 觸發檔案選擇
const triggerFileSelect = () => {
  fileInputRef.value?.click()
}

// 處理檔案選擇
const handleFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    selectFile(input.files[0])
  }
}

// 處理拖放
const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  const files = event.dataTransfer?.files
  if (files && files[0]) {
    selectFile(files[0])
  }
}

// 選擇檔案
const selectFile = (file: File) => {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    alert('請選擇 PDF 檔案')
    return
  }
  selectedFile.value = file
  uploadResult.value = null
  // 重置進度
  progress.value = {
    totalPages: 0,
    currentPage: 0,
    endPage: 0,
    percent: 0,
    batch: 0,
    totalBatches: 0,
    status: '',
    message: ''
  }
}

// 處理進度更新
const handleProgress = (data: OCRProgress) => {
  switch (data.type) {
    case 'start':
      progress.value.totalPages = data.total_pages || 0
      progress.value.status = 'starting'
      progress.value.message = `開始處理，共 ${data.total_pages} 頁`
      break
    case 'info':
      progress.value.totalBatches = data.total_batches || 1
      break
    case 'progress':
      progress.value.currentPage = data.current_page || 0
      progress.value.endPage = data.end_page || 0
      progress.value.percent = data.percent || 0
      progress.value.batch = data.batch || 0
      progress.value.status = data.status || 'processing'
      if (data.status === 'processing') {
        progress.value.message = `正在處理第 ${data.current_page}-${data.end_page} 頁（批次 ${data.batch}/${progress.value.totalBatches}）`
      } else if (data.status === 'completed') {
        progress.value.message = 'OCR 辨識完成'
      }
      break
    case 'status':
      progress.value.message = data.message || ''
      break
    case 'complete':
      progress.value.percent = 100
      progress.value.status = 'completed'
      progress.value.message = '處理完成！'
      break
    case 'error':
      progress.value.status = 'error'
      progress.value.message = data.message || '處理失敗'
      break
  }
}

// 上傳檔案
const handleUpload = async () => {
  if (!selectedFile.value) return

  const result = await uploadPDFWithProgress(
    selectedFile.value,
    saveToDb.value,
    handleProgress
  )
  if (result) {
    uploadResult.value = result
  }
}

// 重置
const resetUpload = () => {
  selectedFile.value = null
  uploadResult.value = null
  progress.value = {
    totalPages: 0,
    currentPage: 0,
    endPage: 0,
    percent: 0,
    batch: 0,
    totalBatches: 0,
    status: '',
    message: ''
  }
}

// 格式化檔案大小
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// Block 類型對應圖示
const blockTypeIcon = (type: string): string => {
  const icons: Record<string, string> = {
    text: 'i-lucide-text',
    header: 'i-lucide-heading',
    table: 'i-lucide-table',
    photo: 'i-lucide-image',
    logo: 'i-lucide-image',
    chart: 'i-lucide-bar-chart',
    list: 'i-lucide-list',
    form_field: 'i-lucide-text-cursor-input',
    stamp: 'i-lucide-stamp',
    signature: 'i-lucide-pen-tool'
  }
  return icons[type] || 'i-lucide-file-text'
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-3 sm:px-4 py-4 sm:py-8">
    <!-- 頁面標題 -->
    <div class="text-center mb-6 sm:mb-8">
      <h1 class="text-2xl sm:text-3xl font-bold mb-2">上傳 PDF 文件</h1>
      <p class="text-sm sm:text-base text-muted px-4">上傳 PDF 檔案進行 OCR 辨識，AI 會自動分析文字、表格、圖片等內容</p>
    </div>

    <!-- 上傳區域 -->
    <UCard v-if="!uploadResult" class="mb-4 sm:mb-6">
      <div
        class="border-2 border-dashed rounded-lg p-6 sm:p-8 text-center transition-colors"
        :class="[
          isDragging ? 'border-primary bg-primary/5' : 'border-gray-300 dark:border-gray-600',
          selectedFile ? 'bg-green-50 dark:bg-green-900/20 border-green-400' : ''
        ]"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <div v-if="!selectedFile">
          <UIcon name="i-lucide-upload-cloud" class="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 text-muted" />
          <p class="text-base sm:text-lg mb-2">拖放 PDF 檔案到這裡</p>
          <p class="text-xs sm:text-sm text-muted mb-4">或點擊下方按鈕選擇檔案</p>
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf"
            class="hidden"
            @change="handleFileSelect"
          >
          <UButton 
            icon="i-lucide-file-plus" 
            variant="outline" 
            size="sm"
            @click="triggerFileSelect"
          >
            選擇檔案
          </UButton>
        </div>

        <div v-else class="flex items-center justify-center gap-3 sm:gap-4">
          <UIcon name="i-lucide-file-check" class="w-10 h-10 sm:w-12 sm:h-12 text-green-500 shrink-0" />
          <div class="text-left min-w-0">
            <p class="font-medium text-sm sm:text-base truncate">{{ selectedFile.name }}</p>
            <p class="text-xs sm:text-sm text-muted">{{ formatFileSize(selectedFile.size) }}</p>
          </div>
          <UButton
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            size="sm"
            @click="selectedFile = null"
          />
        </div>
      </div>

      <!-- 選項 - 響應式 -->
      <div class="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
        <label class="flex items-center gap-2 cursor-pointer">
          <UCheckbox v-model="saveToDb" />
          <span class="text-xs sm:text-sm">儲存到資料庫（可用於後續問答）</span>
        </label>

        <UButton
          :disabled="!selectedFile || loading"
          :loading="loading"
          icon="i-lucide-scan"
          size="md"
          class="w-full sm:w-auto"
          @click="handleUpload"
        >
          {{ loading ? '處理中...' : '開始辨識' }}
        </UButton>
      </div>

      <!-- 錯誤訊息 -->
      <UAlert
        v-if="error"
        color="error"
        icon="i-lucide-alert-circle"
        :title="error"
        class="mt-4"
      />
    </UCard>

    <!-- 處理中狀態（含進度條） -->
    <UCard v-if="loading" class="mb-4 sm:mb-6">
      <div class="py-6 sm:py-8">
        <div class="text-center mb-6">
          <UIcon name="i-lucide-loader-2" class="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-4 animate-spin text-primary" />
          <p class="text-base sm:text-lg font-medium">AI 正在分析文件...</p>
        </div>

        <!-- 進度條 -->
        <div class="max-w-md mx-auto px-4">
          <div class="flex justify-between text-xs sm:text-sm text-muted mb-2">
            <span>{{ progress.message || '準備中...' }}</span>
            <span class="font-medium">{{ progress.percent }}%</span>
          </div>
          
          <!-- 進度條本體 -->
          <div class="h-3 bg-muted/30 rounded-full overflow-hidden">
            <div
              class="h-full bg-primary rounded-full transition-all duration-300 ease-out"
              :style="{ width: `${progress.percent}%` }"
            />
          </div>

          <!-- 詳細資訊 -->
          <div v-if="progress.totalPages > 0" class="mt-3 text-center">
            <p class="text-xs sm:text-sm text-muted">
              <span v-if="progress.status === 'processing'">
                處理中：第 {{ progress.currentPage }}-{{ progress.endPage }} 頁 / 共 {{ progress.totalPages }} 頁
              </span>
              <span v-else-if="progress.status === 'completed'">
                共 {{ progress.totalPages }} 頁處理完成
              </span>
              <span v-else>
                總共 {{ progress.totalPages }} 頁
              </span>
            </p>
            <p v-if="progress.totalBatches > 1" class="text-xs text-muted mt-1">
              批次 {{ progress.batch }} / {{ progress.totalBatches }}
            </p>
          </div>
        </div>

        <p class="text-xs text-muted mt-4 text-center">大型文件會自動分批處理，請耐心等候</p>
      </div>
    </UCard>

    <!-- 辨識結果 -->
    <div v-if="uploadResult">
      <!-- 成功訊息 -->
      <UAlert
        v-if="uploadResult.success"
        color="success"
        icon="i-lucide-check-circle"
        title="辨識完成！"
        :description="`文件已成功處理，共 ${uploadResult.total_pages} 頁，耗時 ${uploadResult.processing_time?.total_formatted || '未知'}`"
        class="mb-4 sm:mb-6"
      />

      <!-- 基本資訊 -->
      <UCard class="mb-4 sm:mb-6">
        <template #header>
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <h2 class="text-base sm:text-lg font-semibold">文件資訊</h2>
            <UButton
              icon="i-lucide-refresh-cw"
              variant="ghost"
              size="xs"
              @click="resetUpload"
            >
              上傳新文件
            </UButton>
          </div>
        </template>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          <div>
            <p class="text-xs sm:text-sm text-muted">文件類型</p>
            <p class="font-medium text-sm sm:text-base">{{ uploadResult.detected_type || '未知' }}</p>
          </div>
          <div>
            <p class="text-xs sm:text-sm text-muted">語言</p>
            <p class="font-medium text-sm sm:text-base">{{ uploadResult.language || '未知' }}</p>
          </div>
          <div>
            <p class="text-xs sm:text-sm text-muted">總頁數</p>
            <p class="font-medium text-sm sm:text-base">{{ uploadResult.total_pages }} 頁</p>
          </div>
          <div>
            <p class="text-xs sm:text-sm text-muted">處理時間</p>
            <p class="font-medium text-sm sm:text-base">{{ uploadResult.processing_time?.total_formatted || '未知' }}</p>
          </div>
        </div>

        <div v-if="uploadResult.document_id" class="mt-4 pt-4 border-t">
          <p class="text-xs sm:text-sm text-muted mb-2">文件 ID</p>
          <div class="flex flex-col sm:flex-row sm:items-center gap-2">
            <code class="text-xs bg-muted/50 px-2 py-1 rounded break-all">{{ uploadResult.document_id }}</code>
            <NuxtLink :to="`/documents/${uploadResult.document_id}`">
              <UButton size="xs" variant="link">
                查看詳情 →
              </UButton>
            </NuxtLink>
          </div>
        </div>
      </UCard>

      <!-- 辨識區塊 -->
      <UCard v-if="uploadResult.blocks.length > 0" class="mb-4 sm:mb-6">
        <template #header>
          <h2 class="text-base sm:text-lg font-semibold">辨識內容（{{ uploadResult.blocks.length }} 個區塊）</h2>
        </template>

        <div class="space-y-2 sm:space-y-3 max-h-72 sm:max-h-96 overflow-y-auto">
          <div
            v-for="block in uploadResult.blocks"
            :key="block.id"
            class="flex gap-2 sm:gap-3 p-2 sm:p-3 rounded-lg bg-muted/30"
          >
            <UIcon :name="blockTypeIcon(block.type)" class="w-4 h-4 sm:w-5 sm:h-5 mt-0.5 text-muted shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="flex flex-wrap items-center gap-1 sm:gap-2 mb-1">
                <UBadge size="xs" variant="subtle">{{ block.type }}</UBadge>
                <span class="text-xs text-muted">第 {{ block.page }} 頁 · {{ block.region }}</span>
              </div>
              <p class="text-xs sm:text-sm break-words">{{ block.content }}</p>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Key-Value Pairs -->
      <UCard v-if="uploadResult.key_value_pairs.length > 0" class="mb-4 sm:mb-6">
        <template #header>
          <h2 class="text-base sm:text-lg font-semibold">擷取的鍵值對</h2>
        </template>

        <div class="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
          <table class="w-full text-xs sm:text-sm min-w-[300px]">
            <thead>
              <tr class="border-b">
                <th class="text-left py-2 px-2 sm:px-3">鍵</th>
                <th class="text-left py-2 px-2 sm:px-3">值</th>
                <th class="text-left py-2 px-2 sm:px-3">頁碼</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(kv, idx) in uploadResult.key_value_pairs" :key="idx" class="border-b last:border-0">
                <td class="py-2 px-2 sm:px-3 font-medium">{{ kv.key }}</td>
                <td class="py-2 px-2 sm:px-3">{{ kv.value }}</td>
                <td class="py-2 px-2 sm:px-3 text-muted">{{ kv.page }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </UCard>

      <!-- 操作按鈕 - 響應式 -->
      <div class="flex flex-col sm:flex-row gap-3 sm:gap-4 sm:justify-center">
        <UButton
          to="/documents"
          icon="i-lucide-folder-open"
          variant="outline"
          class="w-full sm:w-auto"
        >
          查看所有文件
        </UButton>
        <UButton
          to="/ask"
          icon="i-lucide-message-circle"
          class="w-full sm:w-auto"
        >
          開始問答
        </UButton>
      </div>
    </div>
  </div>
</template>
