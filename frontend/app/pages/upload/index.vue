<script setup lang="ts">
import type { OCRResponse } from '~/composables/useApi'

const { uploadPDF, loading, error } = useApi()

// 狀態
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const uploadResult = ref<OCRResponse | null>(null)
const saveToDb = ref(true)

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
}

// 上傳檔案
const handleUpload = async () => {
  if (!selectedFile.value) return

  const result = await uploadPDF(selectedFile.value, saveToDb.value)
  if (result) {
    uploadResult.value = result
  }
}

// 重置
const resetUpload = () => {
  selectedFile.value = null
  uploadResult.value = null
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
  <div class="max-w-4xl mx-auto px-4 py-8">
    <!-- 頁面標題 -->
    <div class="text-center mb-8">
      <h1 class="text-3xl font-bold mb-2">上傳 PDF 文件</h1>
      <p class="text-muted">上傳 PDF 檔案進行 OCR 辨識，AI 會自動分析文字、表格、圖片等內容</p>
    </div>

    <!-- 上傳區域 -->
    <UCard v-if="!uploadResult" class="mb-6">
      <div
        class="border-2 border-dashed rounded-lg p-8 text-center transition-colors"
        :class="[
          isDragging ? 'border-primary bg-primary/5' : 'border-gray-300 dark:border-gray-600',
          selectedFile ? 'bg-green-50 dark:bg-green-900/20 border-green-400' : ''
        ]"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <div v-if="!selectedFile">
          <UIcon name="i-lucide-upload-cloud" class="w-16 h-16 mx-auto mb-4 text-muted" />
          <p class="text-lg mb-2">拖放 PDF 檔案到這裡</p>
          <p class="text-sm text-muted mb-4">或點擊下方按鈕選擇檔案</p>
          <label>
            <UButton icon="i-lucide-file-plus" variant="outline">
              選擇檔案
            </UButton>
            <input
              type="file"
              accept=".pdf"
              class="hidden"
              @change="handleFileSelect"
            >
          </label>
        </div>

        <div v-else class="flex items-center justify-center gap-4">
          <UIcon name="i-lucide-file-check" class="w-12 h-12 text-green-500" />
          <div class="text-left">
            <p class="font-medium">{{ selectedFile.name }}</p>
            <p class="text-sm text-muted">{{ formatFileSize(selectedFile.size) }}</p>
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

      <!-- 選項 -->
      <div class="mt-4 flex items-center justify-between">
        <label class="flex items-center gap-2 cursor-pointer">
          <UCheckbox v-model="saveToDb" />
          <span class="text-sm">儲存到資料庫（可用於後續問答）</span>
        </label>

        <UButton
          :disabled="!selectedFile || loading"
          :loading="loading"
          icon="i-lucide-scan"
          size="lg"
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

    <!-- 處理中狀態 -->
    <UCard v-if="loading" class="mb-6">
      <div class="text-center py-8">
        <UIcon name="i-lucide-loader-2" class="w-12 h-12 mx-auto mb-4 animate-spin text-primary" />
        <p class="text-lg font-medium">AI 正在分析文件...</p>
        <p class="text-sm text-muted mt-2">大型文件可能需要較長時間，請耐心等候</p>
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
        class="mb-6"
      />

      <!-- 基本資訊 -->
      <UCard class="mb-6">
        <template #header>
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold">文件資訊</h2>
            <UButton
              icon="i-lucide-refresh-cw"
              variant="ghost"
              size="sm"
              @click="resetUpload"
            >
              上傳新文件
            </UButton>
          </div>
        </template>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p class="text-sm text-muted">文件類型</p>
            <p class="font-medium">{{ uploadResult.detected_type || '未知' }}</p>
          </div>
          <div>
            <p class="text-sm text-muted">語言</p>
            <p class="font-medium">{{ uploadResult.language || '未知' }}</p>
          </div>
          <div>
            <p class="text-sm text-muted">總頁數</p>
            <p class="font-medium">{{ uploadResult.total_pages }} 頁</p>
          </div>
          <div>
            <p class="text-sm text-muted">處理時間</p>
            <p class="font-medium">{{ uploadResult.processing_time?.total_formatted || '未知' }}</p>
          </div>
        </div>

        <div v-if="uploadResult.document_id" class="mt-4 pt-4 border-t">
          <p class="text-sm text-muted mb-2">文件 ID</p>
          <code class="text-xs bg-muted/50 px-2 py-1 rounded">{{ uploadResult.document_id }}</code>
          <NuxtLink :to="`/documents/${uploadResult.document_id}`">
            <UButton size="sm" variant="link" class="ml-2">
              查看詳情 →
            </UButton>
          </NuxtLink>
        </div>
      </UCard>

      <!-- 辨識區塊 -->
      <UCard v-if="uploadResult.blocks.length > 0" class="mb-6">
        <template #header>
          <h2 class="text-lg font-semibold">辨識內容（{{ uploadResult.blocks.length }} 個區塊）</h2>
        </template>

        <div class="space-y-3 max-h-96 overflow-y-auto">
          <div
            v-for="block in uploadResult.blocks"
            :key="block.id"
            class="flex gap-3 p-3 rounded-lg bg-muted/30"
          >
            <UIcon :name="blockTypeIcon(block.type)" class="w-5 h-5 mt-0.5 text-muted shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <UBadge size="xs" variant="subtle">{{ block.type }}</UBadge>
                <span class="text-xs text-muted">第 {{ block.page }} 頁 · {{ block.region }}</span>
              </div>
              <p class="text-sm break-words">{{ block.content }}</p>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Key-Value Pairs -->
      <UCard v-if="uploadResult.key_value_pairs.length > 0" class="mb-6">
        <template #header>
          <h2 class="text-lg font-semibold">擷取的鍵值對</h2>
        </template>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b">
                <th class="text-left py-2 px-3">鍵</th>
                <th class="text-left py-2 px-3">值</th>
                <th class="text-left py-2 px-3">頁碼</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(kv, idx) in uploadResult.key_value_pairs" :key="idx" class="border-b last:border-0">
                <td class="py-2 px-3 font-medium">{{ kv.key }}</td>
                <td class="py-2 px-3">{{ kv.value }}</td>
                <td class="py-2 px-3 text-muted">{{ kv.page }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </UCard>

      <!-- 操作按鈕 -->
      <div class="flex gap-4 justify-center">
        <UButton
          to="/documents"
          icon="i-lucide-folder-open"
          variant="outline"
        >
          查看所有文件
        </UButton>
        <UButton
          to="/ask"
          icon="i-lucide-message-circle"
        >
          開始問答
        </UButton>
      </div>
    </div>
  </div>
</template>

