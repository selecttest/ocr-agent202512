<script setup lang="ts">
const route = useRoute()
const { getDocument, loading, error } = useApi()

// 文件詳情
const document = ref<Awaited<ReturnType<typeof getDocument>>>(null)

// 當前選中的頁碼（用於篩選）
const selectedPage = ref<number | null>(null)

// 取得文件 ID
const docId = computed(() => route.params.id as string)

// 載入文件詳情
const loadDocument = async () => {
  if (docId.value) {
    document.value = await getDocument(docId.value)
  }
}

// 初始化載入
onMounted(() => {
  loadDocument()
})

// 監聽路由變化
watch(docId, () => {
  loadDocument()
})

// 篩選後的 blocks
const filteredBlocks = computed(() => {
  if (!document.value?.blocks) return []
  if (selectedPage.value === null) return document.value.blocks
  return document.value.blocks.filter(b => b.page === selectedPage.value)
})

// 取得所有頁碼
const allPages = computed(() => {
  if (!document.value?.blocks) return []
  const pages = [...new Set(document.value.blocks.map(b => b.page))]
  return pages.sort((a, b) => a - b)
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
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return dateStr
  }
}

// Block 類型對應圖示和顏色
const getBlockStyle = (type: string) => {
  const styles: Record<string, { icon: string; color: string }> = {
    text: { icon: 'i-lucide-text', color: 'neutral' },
    header: { icon: 'i-lucide-heading', color: 'primary' },
    section_title: { icon: 'i-lucide-heading-2', color: 'primary' },
    table: { icon: 'i-lucide-table', color: 'info' },
    photo: { icon: 'i-lucide-image', color: 'success' },
    logo: { icon: 'i-lucide-image', color: 'warning' },
    chart: { icon: 'i-lucide-bar-chart', color: 'info' },
    list: { icon: 'i-lucide-list', color: 'neutral' },
    form_field: { icon: 'i-lucide-text-cursor-input', color: 'warning' },
    stamp: { icon: 'i-lucide-stamp', color: 'error' },
    signature: { icon: 'i-lucide-pen-tool', color: 'error' },
    footer: { icon: 'i-lucide-footer', color: 'neutral' },
    page_number: { icon: 'i-lucide-hash', color: 'neutral' }
  }
  return styles[type] || { icon: 'i-lucide-file-text', color: 'neutral' }
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <!-- 返回按鈕 -->
    <UButton
      to="/documents"
      icon="i-lucide-arrow-left"
      variant="ghost"
      class="mb-6"
    >
      返回文件列表
    </UButton>

    <!-- 載入中 -->
    <div v-if="loading" class="text-center py-16">
      <UIcon name="i-lucide-loader-2" class="w-12 h-12 mx-auto mb-4 animate-spin text-primary" />
      <p class="text-muted">載入中...</p>
    </div>

    <!-- 錯誤訊息 -->
    <UAlert
      v-else-if="error"
      color="error"
      icon="i-lucide-alert-circle"
      :title="error"
      class="mb-6"
    >
      <template #actions>
        <UButton variant="outline" size="sm" @click="loadDocument">
          重試
        </UButton>
      </template>
    </UAlert>

    <!-- 文件詳情 -->
    <div v-else-if="document">
      <!-- 標題 -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold mb-2">{{ document.document.filename }}</h1>
        <p class="text-muted">上傳於 {{ formatDate(document.document.upload_time) }}</p>
      </div>

      <!-- 基本資訊卡片 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <UCard>
          <div class="text-center">
            <UIcon name="i-lucide-file-type" class="w-8 h-8 mx-auto mb-2 text-primary" />
            <p class="text-sm text-muted">文件類型</p>
            <p class="font-semibold">{{ document.document.detected_type || '未知' }}</p>
          </div>
        </UCard>

        <UCard>
          <div class="text-center">
            <UIcon name="i-lucide-languages" class="w-8 h-8 mx-auto mb-2 text-primary" />
            <p class="text-sm text-muted">語言</p>
            <p class="font-semibold">{{ document.document.language || '未知' }}</p>
          </div>
        </UCard>

        <UCard>
          <div class="text-center">
            <UIcon name="i-lucide-file" class="w-8 h-8 mx-auto mb-2 text-primary" />
            <p class="text-sm text-muted">總頁數</p>
            <p class="font-semibold">{{ document.document.total_pages }} 頁</p>
          </div>
        </UCard>

        <UCard>
          <div class="text-center">
            <UIcon name="i-lucide-clock" class="w-8 h-8 mx-auto mb-2 text-primary" />
            <p class="text-sm text-muted">處理時間</p>
            <p class="font-semibold">{{ document.document.processing_time_seconds?.toFixed(1) || '未知' }} 秒</p>
          </div>
        </UCard>
      </div>

      <!-- 摘要 -->
      <UCard v-if="document.document.summary" class="mb-8">
        <template #header>
          <h2 class="text-lg font-semibold flex items-center gap-2">
            <UIcon name="i-lucide-file-text" class="w-5 h-5" />
            文件摘要
          </h2>
        </template>
        <p class="whitespace-pre-wrap">{{ document.document.summary }}</p>
      </UCard>

      <!-- 辨識內容 -->
      <UCard class="mb-8">
        <template #header>
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold flex items-center gap-2">
              <UIcon name="i-lucide-scan-text" class="w-5 h-5" />
              辨識內容（{{ document.blocks.length }} 個區塊）
            </h2>

            <!-- 頁碼篩選 -->
            <div class="flex items-center gap-2">
              <span class="text-sm text-muted">篩選頁碼：</span>
              <UButtonGroup>
                <UButton
                  size="xs"
                  :variant="selectedPage === null ? 'solid' : 'outline'"
                  @click="selectedPage = null"
                >
                  全部
                </UButton>
                <UButton
                  v-for="page in allPages"
                  :key="page"
                  size="xs"
                  :variant="selectedPage === page ? 'solid' : 'outline'"
                  @click="selectedPage = page"
                >
                  {{ page }}
                </UButton>
              </UButtonGroup>
            </div>
          </div>
        </template>

        <div class="space-y-3 max-h-[600px] overflow-y-auto">
          <div
            v-for="block in filteredBlocks"
            :key="block.id"
            class="flex gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
          >
            <UIcon
              :name="getBlockStyle(block.block_type).icon"
              class="w-5 h-5 mt-0.5 shrink-0"
              :class="`text-${getBlockStyle(block.block_type).color}`"
            />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <UBadge size="xs" :color="getBlockStyle(block.block_type).color as any" variant="subtle">
                  {{ block.block_type }}
                </UBadge>
                <span class="text-xs text-muted">
                  第 {{ block.page }} 頁 · {{ block.region }}
                </span>
                <span v-if="block.confidence" class="text-xs text-muted">
                  · 信心度 {{ (block.confidence * 100).toFixed(0) }}%
                </span>
              </div>
              <p class="text-sm break-words whitespace-pre-wrap">{{ block.content }}</p>
            </div>
          </div>

          <div v-if="filteredBlocks.length === 0" class="text-center py-8 text-muted">
            此頁沒有辨識到內容
          </div>
        </div>
      </UCard>

      <!-- Key-Value Pairs -->
      <UCard v-if="document.key_values.length > 0" class="mb-8">
        <template #header>
          <h2 class="text-lg font-semibold flex items-center gap-2">
            <UIcon name="i-lucide-list-tree" class="w-5 h-5" />
            擷取的鍵值對（{{ document.key_values.length }} 項）
          </h2>
        </template>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b">
                <th class="text-left py-2 px-3 font-medium">鍵</th>
                <th class="text-left py-2 px-3 font-medium">值</th>
                <th class="text-left py-2 px-3 font-medium">頁碼</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="kv in document.key_values"
                :key="kv.id"
                class="border-b last:border-0 hover:bg-muted/30"
              >
                <td class="py-2 px-3 font-medium">{{ kv.key }}</td>
                <td class="py-2 px-3">{{ kv.value }}</td>
                <td class="py-2 px-3 text-muted">{{ kv.page }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </UCard>

      <!-- 圖片摘要 -->
      <UCard v-if="document.images.length > 0" class="mb-8">
        <template #header>
          <h2 class="text-lg font-semibold flex items-center gap-2">
            <UIcon name="i-lucide-images" class="w-5 h-5" />
            圖片摘要（{{ document.images.length }} 張）
          </h2>
        </template>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="img in document.images"
            :key="img.id"
            class="flex gap-3 p-3 rounded-lg bg-muted/30"
          >
            <UIcon name="i-lucide-image" class="w-8 h-8 shrink-0 text-muted" />
            <div>
              <div class="flex items-center gap-2 mb-1">
                <UBadge size="xs" variant="subtle">{{ img.image_type }}</UBadge>
                <span class="text-xs text-muted">第 {{ img.page }} 頁 · {{ img.region }}</span>
              </div>
              <p class="text-sm">{{ img.description }}</p>
            </div>
          </div>
        </div>
      </UCard>

      <!-- 操作按鈕 -->
      <div class="flex gap-4 justify-center">
        <UButton
          to="/ask"
          icon="i-lucide-message-circle"
        >
          針對此文件提問
        </UButton>
        <UButton
          to="/upload"
          icon="i-lucide-upload"
          variant="outline"
        >
          上傳更多文件
        </UButton>
      </div>
    </div>
  </div>
</template>

