<script setup lang="ts">
import type { AskResponse, DocumentItem } from '~/composables/useApi'

const { askQuestion, askQuestionWithDocs, getDocuments, deleteDocument, deleteDocuments, loading, error } = useApi()

// 狀態
const question = ref('')
const topK = ref(5)
const conversations = ref<Array<{
  type: 'user' | 'assistant'
  content: string
  sources?: AskResponse['sources']
  timestamp: Date
}>>([])

// 文件列表和選擇
const documents = ref<DocumentItem[]>([])
const selectedDocIds = ref<string[]>([])
const showDocSelector = ref(false)
const isLoadingDocs = ref(false)
const isDeleting = ref(false)
const showDeleteConfirm = ref(false)
const deleteTargetId = ref<string | null>(null)

// 載入文件列表
const loadDocuments = async () => {
  isLoadingDocs.value = true
  documents.value = await getDocuments(100)
  isLoadingDocs.value = false
}

// 初始化載入
onMounted(() => {
  loadDocuments()
})

// 計算選中的文件數量
const selectedCount = computed(() => selectedDocIds.value.length)
const documentCount = computed(() => documents.value.length)

// 切換文件選擇
const toggleDocSelection = (docId: string) => {
  const idx = selectedDocIds.value.indexOf(docId)
  if (idx > -1) {
    selectedDocIds.value.splice(idx, 1)
  } else {
    selectedDocIds.value.push(docId)
  }
}

// 全選/取消全選
const toggleSelectAll = () => {
  if (selectedDocIds.value.length === documents.value.length) {
    selectedDocIds.value = []
  } else {
    selectedDocIds.value = documents.value.map(d => d.id)
  }
}

// 清除選擇
const clearSelection = () => {
  selectedDocIds.value = []
}

// 刪除單一文件
const handleDeleteSingle = async (docId: string) => {
  deleteTargetId.value = docId
  showDeleteConfirm.value = true
}

// 刪除選中的文件
const handleDeleteSelected = async () => {
  if (selectedDocIds.value.length === 0) return
  deleteTargetId.value = null
  showDeleteConfirm.value = true
}

// 確認刪除
const confirmDelete = async () => {
  isDeleting.value = true

  if (deleteTargetId.value) {
    // 刪除單一文件
    const result = await deleteDocument(deleteTargetId.value)
    if (result?.success) {
      documents.value = documents.value.filter(d => d.id !== deleteTargetId.value)
      selectedDocIds.value = selectedDocIds.value.filter(id => id !== deleteTargetId.value)
    }
  } else {
    // 批次刪除
    const result = await deleteDocuments(selectedDocIds.value)
    if (result) {
      documents.value = documents.value.filter(d => !result.deleted_ids.includes(d.id))
      selectedDocIds.value = []
    }
  }

  isDeleting.value = false
  showDeleteConfirm.value = false
  deleteTargetId.value = null
}

// 取消刪除
const cancelDelete = () => {
  showDeleteConfirm.value = false
  deleteTargetId.value = null
}

// 送出問題
const handleAsk = async () => {
  if (!question.value.trim() || loading.value) return

  const userQuestion = question.value.trim()
  question.value = ''

  // 加入用戶訊息
  conversations.value.push({
    type: 'user',
    content: userQuestion,
    timestamp: new Date()
  })

  // 呼叫 API（根據是否有選擇文件決定使用哪個方法）
  let result: AskResponse | null
  if (selectedDocIds.value.length > 0) {
    result = await askQuestionWithDocs(userQuestion, selectedDocIds.value, topK.value)
  } else {
    result = await askQuestion(userQuestion, topK.value)
  }

  if (result) {
    conversations.value.push({
      type: 'assistant',
      content: result.answer,
      sources: result.sources,
      timestamp: new Date()
    })
  } else {
    conversations.value.push({
      type: 'assistant',
      content: error.value || '抱歉，發生錯誤，請稍後再試。',
      timestamp: new Date()
    })
  }

  // 滾動到底部
  await nextTick()
  scrollToBottom()
}

// 滾動到底部
const chatContainer = ref<HTMLElement | null>(null)
const scrollToBottom = () => {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

// 清除對話
const clearConversations = () => {
  conversations.value = []
}

// 快捷問題
const quickQuestions = [
  '這份文件的主要內容是什麼？',
  '文件中提到了哪些重要日期？',
  '有哪些關鍵的數字或金額？',
  '文件的結論或建議是什麼？'
]

const askQuickQuestion = (q: string) => {
  question.value = q
  handleAsk()
}

// 格式化時間
const formatTime = (date: Date): string => {
  return date.toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化日期
const formatDate = (dateStr: string): string => {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-TW', {
      month: 'short',
      day: 'numeric'
    })
  } catch {
    return ''
  }
}
</script>

<template>
  <div class="h-[calc(100vh-120px)] md:h-[calc(100vh-140px)] flex flex-col px-2 sm:px-4 py-2 sm:py-4">
    <!-- 頁面標題 - 響應式 -->
    <div class="mb-3 sm:mb-4 flex-shrink-0">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 class="text-xl sm:text-2xl md:text-3xl font-bold">AI 文件問答</h1>
          <p class="text-xs sm:text-sm text-muted mt-1">
            <span v-if="documentCount > 0">
              共 {{ documentCount }} 份文件
              <span v-if="selectedCount > 0" class="text-primary font-medium">
                ・已選 {{ selectedCount }} 份
              </span>
            </span>
            <span v-else>尚無文件</span>
          </p>
        </div>

        <!-- 文件選擇按鈕 -->
        <UButton
          v-if="documentCount > 0"
          :icon="showDocSelector ? 'i-lucide-x' : 'i-lucide-files'"
          :variant="selectedCount > 0 ? 'solid' : 'outline'"
          size="sm"
          @click="showDocSelector = !showDocSelector"
        >
          <span class="hidden sm:inline">{{ showDocSelector ? '關閉' : '選擇文件' }}</span>
          <span class="sm:hidden">{{ selectedCount > 0 ? selectedCount : '選擇' }}</span>
        </UButton>
      </div>
    </div>

    <!-- 無文件提示 -->
    <UAlert
      v-if="documentCount === 0 && !isLoadingDocs"
      color="warning"
      icon="i-lucide-alert-triangle"
      title="尚無可查詢的文件"
      description="請先上傳 PDF 文件，才能進行問答"
      class="mb-3 flex-shrink-0"
    >
      <template #actions>
        <UButton to="/upload" size="sm">
          上傳文件
        </UButton>
      </template>
    </UAlert>

    <!-- 主要內容區 - 固定高度 -->
    <div class="flex-1 flex flex-col lg:flex-row gap-3 min-h-0 overflow-hidden">
      <!-- 文件選擇側邊欄 - 響應式 -->
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 -translate-x-4 lg:translate-x-0 lg:-translate-y-4"
        enter-to-class="opacity-100 translate-x-0 lg:translate-y-0"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="opacity-100 translate-x-0 lg:translate-y-0"
        leave-to-class="opacity-0 -translate-x-4 lg:translate-x-0 lg:-translate-y-4"
      >
        <UCard
          v-if="showDocSelector"
          class="lg:w-72 xl:w-80 flex-shrink-0 flex flex-col max-h-48 lg:max-h-full"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <h3 class="font-semibold text-sm">選擇查詢文件</h3>
              <div class="flex gap-1">
                <UButton
                  size="xs"
                  variant="ghost"
                  @click="toggleSelectAll"
                >
                  {{ selectedDocIds.length === documents.length ? '取消全選' : '全選' }}
                </UButton>
                <UButton
                  v-if="selectedCount > 0"
                  size="xs"
                  variant="ghost"
                  color="neutral"
                  @click="clearSelection"
                >
                  清除
                </UButton>
              </div>
            </div>
          </template>

          <!-- 文件列表 - 可捲動 -->
          <div class="flex-1 overflow-y-auto -mx-4 px-4 space-y-1">
            <div
              v-for="doc in documents"
              :key="doc.id"
              class="group flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors"
              :class="selectedDocIds.includes(doc.id)
                ? 'bg-primary/10 border border-primary/30'
                : 'hover:bg-muted/50 border border-transparent'"
              @click="toggleDocSelection(doc.id)"
            >
              <UCheckbox
                :model-value="selectedDocIds.includes(doc.id)"
                @click.stop
                @update:model-value="toggleDocSelection(doc.id)"
              />
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate">{{ doc.filename }}</p>
                <p class="text-xs text-muted">
                  {{ doc.total_pages }} 頁 · {{ formatDate(doc.upload_time) }}
                </p>
              </div>
              <!-- 刪除按鈕 -->
              <UButton
                icon="i-lucide-trash-2"
                size="xs"
                variant="ghost"
                color="error"
                class="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                @click.stop="handleDeleteSingle(doc.id)"
              />
            </div>
          </div>

          <template #footer>
            <div class="flex items-center justify-between">
              <p class="text-xs text-muted">
                {{ selectedCount > 0 ? `已選 ${selectedCount} 份` : '搜尋所有文件' }}
              </p>
              <UButton
                v-if="selectedCount > 0"
                icon="i-lucide-trash-2"
                size="xs"
                variant="soft"
                color="error"
                @click="handleDeleteSelected"
              >
                刪除選中
              </UButton>
            </div>
          </template>
        </UCard>
      </Transition>

      <!-- 對話區域 - 固定大小 -->
      <div class="flex-1 flex flex-col min-h-0 border rounded-lg bg-background shadow-sm">
        <!-- 對話內容 - 固定高度可捲動 -->
        <div
          ref="chatContainer"
          class="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4"
          style="min-height: 0;"
        >
          <!-- 空狀態 -->
          <div v-if="conversations.length === 0" class="h-full flex flex-col items-center justify-center py-8">
            <UIcon name="i-lucide-message-circle" class="w-12 h-12 sm:w-16 sm:h-16 text-muted mb-3 sm:mb-4" />
            <h2 class="text-lg sm:text-xl font-semibold mb-2">開始提問</h2>
            <p class="text-muted text-center text-sm mb-4 sm:mb-6 px-4">
              輸入你想了解的問題，AI 會根據
              {{ selectedCount > 0 ? '選擇的文件' : '已上傳的文件' }}
              回答
            </p>

            <!-- 快捷問題 - 響應式 -->
            <div class="flex flex-wrap gap-2 justify-center max-w-lg px-2">
              <UButton
                v-for="q in quickQuestions"
                :key="q"
                size="xs"
                variant="outline"
                class="text-xs"
                @click="askQuickQuestion(q)"
              >
                {{ q }}
              </UButton>
            </div>
          </div>

          <!-- 對話訊息 -->
          <div
            v-for="(msg, idx) in conversations"
            :key="idx"
            class="flex gap-2 sm:gap-3"
            :class="msg.type === 'user' ? 'justify-end' : 'justify-start'"
          >
            <!-- AI 頭像 -->
            <div
              v-if="msg.type === 'assistant'"
              class="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0"
            >
              <UIcon name="i-lucide-bot" class="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
            </div>

            <!-- 訊息內容 -->
            <div
              class="max-w-[85%] sm:max-w-[80%] rounded-lg p-3 sm:p-4"
              :class="msg.type === 'user'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted/50'"
            >
              <p class="whitespace-pre-wrap text-sm sm:text-base">{{ msg.content }}</p>

              <!-- 來源引用 - 響應式 -->
              <div v-if="msg.sources && msg.sources.length > 0" class="mt-3 pt-2 sm:pt-3 border-t border-current/10">
                <p class="text-xs opacity-70 mb-2">📚 參考來源：</p>
                <div class="space-y-2">
                  <div
                    v-for="(source, sIdx) in msg.sources"
                    :key="sIdx"
                    class="text-xs p-2 rounded bg-black/5 dark:bg-white/5"
                  >
                    <div class="flex flex-wrap items-center gap-1 sm:gap-2 mb-1">
                      <span class="font-medium truncate max-w-[150px] sm:max-w-none">{{ source.filename }}</span>
                      <UBadge size="xs" variant="subtle">第 {{ source.page }} 頁</UBadge>
                      <span v-if="source.similarity" class="opacity-70">
                        {{ (source.similarity * 100).toFixed(0) }}%
                      </span>
                    </div>
                    <p class="opacity-70 line-clamp-2">{{ source.content }}</p>
                  </div>
                </div>
              </div>

              <!-- 時間戳 -->
              <p class="text-xs opacity-50 mt-2">{{ formatTime(msg.timestamp) }}</p>
            </div>

            <!-- 用戶頭像 -->
            <div
              v-if="msg.type === 'user'"
              class="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-primary flex items-center justify-center shrink-0"
            >
              <UIcon name="i-lucide-user" class="w-4 h-4 sm:w-5 sm:h-5 text-primary-foreground" />
            </div>
          </div>

          <!-- 載入中 -->
          <div v-if="loading" class="flex gap-2 sm:gap-3">
            <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
              <UIcon name="i-lucide-bot" class="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
            </div>
            <div class="bg-muted/50 rounded-lg p-3 sm:p-4">
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
                <span class="text-sm">AI 正在思考...</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 輸入區域 - 固定在底部 -->
        <div class="border-t p-3 sm:p-4 flex-shrink-0">
          <!-- 控制列 -->
          <div class="flex items-center gap-2 mb-2 flex-wrap">
            <UButton
              v-if="conversations.length > 0"
              icon="i-lucide-trash-2"
              variant="ghost"
              size="xs"
              color="neutral"
              @click="clearConversations"
            >
              <span class="hidden sm:inline">清除對話</span>
            </UButton>

            <!-- 選中文件提示 -->
            <div v-if="selectedCount > 0" class="flex items-center gap-1 text-xs text-primary">
              <UIcon name="i-lucide-filter" class="w-3 h-3" />
              <span>查詢 {{ selectedCount }} 份文件</span>
            </div>

            <div class="flex-1" />

            <label class="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm text-muted">
              <span class="hidden sm:inline">參考數量：</span>
              <span class="sm:hidden">Top:</span>
              <USelect
                v-model="topK"
                :items="[3, 5, 10, 15, 20]"
                size="xs"
                class="w-14 sm:w-16"
              />
            </label>
          </div>

          <!-- 輸入框 -->
          <form @submit.prevent="handleAsk" class="flex gap-2">
            <UInput
              v-model="question"
              placeholder="輸入你的問題..."
              :disabled="loading || documentCount === 0"
              class="flex-1"
              size="md"
            />
            <UButton
              type="submit"
              :disabled="!question.trim() || loading || documentCount === 0"
              :loading="loading"
              icon="i-lucide-send"
              size="md"
            >
              <span class="hidden sm:inline">送出</span>
            </UButton>
          </form>
        </div>
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
            <span v-if="deleteTargetId">
              確定要刪除這份文件嗎？此操作無法復原。
            </span>
            <span v-else>
              確定要刪除選中的 <strong>{{ selectedCount }}</strong> 份文件嗎？此操作無法復原。
            </span>
          </p>

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
