<script setup lang="ts">
const { getDocuments, deleteDocument, loading, error } = useApi()

// 文件列表
const documents = ref<Awaited<ReturnType<typeof getDocuments>>>([])

// 刪除相關狀態
const isDeleting = ref(false)
const showDeleteConfirm = ref(false)
const deleteTargetId = ref<string | null>(null)
const deleteTargetName = ref('')

// 載入文件
const loadDocuments = async () => {
  documents.value = await getDocuments(50)
}

// 初始化載入
onMounted(() => {
  loadDocuments()
})

// 格式化日期
const formatDate = (dateStr: string): string => {
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

// 格式化日期（簡短版）
const formatDateShort = (dateStr: string): string => {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-TW', {
      month: 'short',
      day: 'numeric'
    })
  } catch {
    return dateStr
  }
}

// 文件類型圖示
const getDocTypeIcon = (type: string): string => {
  const icons: Record<string, string> = {
    '合約': 'i-lucide-file-signature',
    '報告': 'i-lucide-file-bar-chart',
    '表單': 'i-lucide-file-input',
    '發票': 'i-lucide-receipt',
    '信件': 'i-lucide-mail'
  }
  return icons[type] || 'i-lucide-file-text'
}

// 開啟刪除確認
const handleDelete = (docId: string, filename: string, event: Event) => {
  event.preventDefault()
  event.stopPropagation()
  deleteTargetId.value = docId
  deleteTargetName.value = filename
  showDeleteConfirm.value = true
}

// 確認刪除
const confirmDelete = async () => {
  if (!deleteTargetId.value) return

  isDeleting.value = true
  const result = await deleteDocument(deleteTargetId.value)

  if (result?.success) {
    documents.value = documents.value.filter(d => d.id !== deleteTargetId.value)
  }

  isDeleting.value = false
  showDeleteConfirm.value = false
  deleteTargetId.value = null
  deleteTargetName.value = ''
}

// 取消刪除
const cancelDelete = () => {
  showDeleteConfirm.value = false
  deleteTargetId.value = null
  deleteTargetName.value = ''
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-3 sm:px-4 py-4 sm:py-8">
    <!-- 頁面標題 - 響應式 -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6 sm:mb-8">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold mb-1 sm:mb-2">文件列表</h1>
        <p class="text-sm text-muted">所有已上傳並處理的 PDF 文件</p>
      </div>
      <UButton
        to="/upload"
        icon="i-lucide-upload"
        size="sm"
        class="w-full sm:w-auto"
      >
        上傳新文件
      </UButton>
    </div>

    <!-- 載入中 -->
    <div v-if="loading && !isDeleting" class="text-center py-12 sm:py-16">
      <UIcon name="i-lucide-loader-2" class="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-4 animate-spin text-primary" />
      <p class="text-muted">載入中...</p>
    </div>

    <!-- 錯誤訊息 -->
    <UAlert
      v-else-if="error && !isDeleting"
      color="error"
      icon="i-lucide-alert-circle"
      :title="error"
      class="mb-6"
    >
      <template #actions>
        <UButton variant="outline" size="sm" @click="loadDocuments">
          重試
        </UButton>
      </template>
    </UAlert>

    <!-- 空狀態 -->
    <UCard v-else-if="documents.length === 0" class="text-center py-12 sm:py-16">
      <UIcon name="i-lucide-folder-open" class="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-4 text-muted" />
      <h2 class="text-lg sm:text-xl font-semibold mb-2">尚無文件</h2>
      <p class="text-muted mb-6 text-sm sm:text-base">上傳你的第一份 PDF 文件開始使用</p>
      <UButton to="/upload" icon="i-lucide-upload">
        上傳文件
      </UButton>
    </UCard>

    <!-- 文件列表 -->
    <div v-else class="space-y-3 sm:space-y-4">
      <!-- 統計 -->
      <div class="flex items-center justify-between mb-3 sm:mb-4">
        <p class="text-sm text-muted">共 {{ documents.length }} 份文件</p>
        <UButton
          icon="i-lucide-refresh-cw"
          variant="ghost"
          size="xs"
          :loading="loading"
          @click="loadDocuments"
        >
          <span class="hidden sm:inline">重新整理</span>
        </UButton>
      </div>

      <!-- 文件卡片 - 響應式 -->
      <div
        v-for="doc in documents"
        :key="doc.id"
        class="group"
      >
        <NuxtLink
          :to="`/documents/${doc.id}`"
          class="block"
        >
          <UCard
            class="hover:shadow-lg transition-shadow cursor-pointer hover:border-primary"
          >
            <div class="flex items-center gap-3 sm:gap-4">
              <!-- 圖示 -->
              <div class="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <UIcon :name="getDocTypeIcon(doc.detected_type)" class="w-5 h-5 sm:w-6 sm:h-6 text-primary" />
              </div>

              <!-- 資訊 -->
              <div class="flex-1 min-w-0">
                <h3 class="font-semibold text-sm sm:text-base truncate">{{ doc.filename }}</h3>
                
                <!-- 桌面版資訊 -->
                <div class="hidden sm:flex items-center gap-3 mt-1 text-sm text-muted">
                  <span class="flex items-center gap-1">
                    <UIcon name="i-lucide-file-type" class="w-4 h-4" />
                    {{ doc.detected_type || '未知類型' }}
                  </span>
                  <span class="flex items-center gap-1">
                    <UIcon name="i-lucide-languages" class="w-4 h-4" />
                    {{ doc.language || '未知' }}
                  </span>
                  <span class="flex items-center gap-1">
                    <UIcon name="i-lucide-file" class="w-4 h-4" />
                    {{ doc.total_pages }} 頁
                  </span>
                </div>
                
                <!-- 移動版資訊 -->
                <div class="sm:hidden flex items-center gap-2 mt-1 text-xs text-muted">
                  <span>{{ doc.detected_type || '未知' }}</span>
                  <span>·</span>
                  <span>{{ doc.total_pages }} 頁</span>
                  <span>·</span>
                  <span>{{ formatDateShort(doc.upload_time) }}</span>
                </div>
              </div>

              <!-- 日期和操作 - 桌面版 -->
              <div class="hidden sm:flex items-center gap-3 shrink-0">
                <p class="text-sm text-muted">{{ formatDate(doc.upload_time) }}</p>
                <UButton
                  icon="i-lucide-trash-2"
                  size="xs"
                  variant="ghost"
                  color="error"
                  class="opacity-0 group-hover:opacity-100 transition-opacity"
                  @click="handleDelete(doc.id, doc.filename, $event)"
                />
                <UIcon name="i-lucide-chevron-right" class="w-5 h-5 text-muted" />
              </div>
              
              <!-- 操作 - 移動版 -->
              <div class="sm:hidden flex items-center gap-2 shrink-0">
                <UButton
                  icon="i-lucide-trash-2"
                  size="xs"
                  variant="ghost"
                  color="error"
                  @click="handleDelete(doc.id, doc.filename, $event)"
                />
                <UIcon name="i-lucide-chevron-right" class="w-5 h-5 text-muted" />
              </div>
            </div>
          </UCard>
        </NuxtLink>
      </div>
    </div>

    <!-- 刪除確認對話框 -->
    <UModal v-model:open="showDeleteConfirm">
      <template #content>
        <UCard>
          <template #header>
            <div class="flex items-center gap-2 text-error">
              <UIcon name="i-lucide-alert-triangle" class="w-5 h-5" />
              <span class="font-semibold">確認刪除</span>
            </div>
          </template>

          <p class="text-sm">
            確定要刪除文件 <strong class="break-all">{{ deleteTargetName }}</strong> 嗎？
          </p>
          <p class="text-xs text-muted mt-2">此操作無法復原，相關的 OCR 資料和向量也會一併刪除。</p>

          <template #footer>
            <div class="flex justify-end gap-2">
              <UButton
                variant="ghost"
                @click="cancelDelete"
              >
                取消
              </UButton>
              <UButton
                color="error"
                :loading="isDeleting"
                @click="confirmDelete"
              >
                確認刪除
              </UButton>
            </div>
          </template>
        </UCard>
      </template>
    </UModal>
  </div>
</template>
