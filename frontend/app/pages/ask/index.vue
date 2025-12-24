<script setup lang="ts">
import type { AskResponse } from '~/composables/useApi'

const { askQuestion, getDocuments, loading, error } = useApi()

// 狀態
const question = ref('')
const topK = ref(5)
const conversations = ref<Array<{
  type: 'user' | 'assistant'
  content: string
  sources?: AskResponse['sources']
  timestamp: Date
}>>([])

// 文件數量（用於提示）
const documentCount = ref(0)

// 載入文件數量
onMounted(async () => {
  const docs = await getDocuments(100)
  documentCount.value = docs.length
})

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

  // 呼叫 API
  const result = await askQuestion(userQuestion, topK.value)

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
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8 h-[calc(100vh-200px)] flex flex-col">
    <!-- 頁面標題 -->
    <div class="mb-6">
      <h1 class="text-3xl font-bold mb-2">AI 文件問答</h1>
      <p class="text-muted">
        針對已上傳的文件進行智能問答，AI 會根據文件內容回答並引用來源
        <span v-if="documentCount > 0" class="text-primary">
          （目前有 {{ documentCount }} 份文件可供查詢）
        </span>
      </p>
    </div>

    <!-- 無文件提示 -->
    <UAlert
      v-if="documentCount === 0"
      color="warning"
      icon="i-lucide-alert-triangle"
      title="尚無可查詢的文件"
      description="請先上傳 PDF 文件，才能進行問答"
      class="mb-6"
    >
      <template #actions>
        <UButton to="/upload" size="sm">
          上傳文件
        </UButton>
      </template>
    </UAlert>

    <!-- 對話區域 -->
    <UCard class="flex-1 flex flex-col overflow-hidden">
      <!-- 對話內容 -->
      <div
        ref="chatContainer"
        class="flex-1 overflow-y-auto p-4 space-y-4"
      >
        <!-- 空狀態 -->
        <div v-if="conversations.length === 0" class="h-full flex flex-col items-center justify-center">
          <UIcon name="i-lucide-message-circle" class="w-16 h-16 text-muted mb-4" />
          <h2 class="text-xl font-semibold mb-2">開始提問</h2>
          <p class="text-muted text-center mb-6">
            輸入你想了解的問題，AI 會根據已上傳的文件回答
          </p>

          <!-- 快捷問題 -->
          <div class="flex flex-wrap gap-2 justify-center max-w-lg">
            <UButton
              v-for="q in quickQuestions"
              :key="q"
              size="sm"
              variant="outline"
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
          class="flex gap-3"
          :class="msg.type === 'user' ? 'justify-end' : 'justify-start'"
        >
          <!-- AI 頭像 -->
          <div
            v-if="msg.type === 'assistant'"
            class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0"
          >
            <UIcon name="i-lucide-bot" class="w-5 h-5 text-primary" />
          </div>

          <!-- 訊息內容 -->
          <div
            class="max-w-[80%] rounded-lg p-4"
            :class="msg.type === 'user'
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted/50'"
          >
            <p class="whitespace-pre-wrap">{{ msg.content }}</p>

            <!-- 來源引用 -->
            <div v-if="msg.sources && msg.sources.length > 0" class="mt-4 pt-3 border-t border-current/10">
              <p class="text-xs opacity-70 mb-2">📚 參考來源：</p>
              <div class="space-y-2">
                <div
                  v-for="(source, sIdx) in msg.sources"
                  :key="sIdx"
                  class="text-xs p-2 rounded bg-black/5 dark:bg-white/5"
                >
                  <div class="flex items-center gap-2 mb-1">
                    <span class="font-medium">{{ source.filename }}</span>
                    <UBadge size="xs" variant="subtle">第 {{ source.page }} 頁</UBadge>
                    <span v-if="source.similarity" class="opacity-70">
                      相似度 {{ (source.similarity * 100).toFixed(0) }}%
                    </span>
                  </div>
                  <p class="opacity-70">{{ source.content }}</p>
                </div>
              </div>
            </div>

            <!-- 時間戳 -->
            <p class="text-xs opacity-50 mt-2">{{ formatTime(msg.timestamp) }}</p>
          </div>

          <!-- 用戶頭像 -->
          <div
            v-if="msg.type === 'user'"
            class="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0"
          >
            <UIcon name="i-lucide-user" class="w-5 h-5 text-primary-foreground" />
          </div>
        </div>

        <!-- 載入中 -->
        <div v-if="loading" class="flex gap-3">
          <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
            <UIcon name="i-lucide-bot" class="w-5 h-5 text-primary" />
          </div>
          <div class="bg-muted/50 rounded-lg p-4">
            <div class="flex items-center gap-2">
              <UIcon name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
              <span>AI 正在思考...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 輸入區域 -->
      <div class="border-t p-4">
        <div class="flex items-center gap-2 mb-2">
          <UButton
            v-if="conversations.length > 0"
            icon="i-lucide-trash-2"
            variant="ghost"
            size="xs"
            color="neutral"
            @click="clearConversations"
          >
            清除對話
          </UButton>

          <div class="flex-1" />

          <label class="flex items-center gap-2 text-sm text-muted">
            參考數量：
            <USelect
              v-model="topK"
              :items="[3, 5, 10, 15, 20]"
              size="xs"
              class="w-16"
            />
          </label>
        </div>

        <form @submit.prevent="handleAsk" class="flex gap-2">
          <UInput
            v-model="question"
            placeholder="輸入你的問題..."
            :disabled="loading || documentCount === 0"
            class="flex-1"
            size="lg"
          />
          <UButton
            type="submit"
            :disabled="!question.trim() || loading || documentCount === 0"
            :loading="loading"
            icon="i-lucide-send"
            size="lg"
          >
            送出
          </UButton>
        </form>
      </div>
    </UCard>
  </div>
</template>

