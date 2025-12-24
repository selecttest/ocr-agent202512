<script setup lang="ts">
const { getDocuments, loading, error } = useApi()

// 文件列表
const documents = ref<Awaited<ReturnType<typeof getDocuments>>>([])

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
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <!-- 頁面標題 -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold mb-2">文件列表</h1>
        <p class="text-muted">所有已上傳並處理的 PDF 文件</p>
      </div>
      <UButton
        to="/upload"
        icon="i-lucide-upload"
      >
        上傳新文件
      </UButton>
    </div>

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
        <UButton variant="outline" size="sm" @click="loadDocuments">
          重試
        </UButton>
      </template>
    </UAlert>

    <!-- 空狀態 -->
    <UCard v-else-if="documents.length === 0" class="text-center py-16">
      <UIcon name="i-lucide-folder-open" class="w-16 h-16 mx-auto mb-4 text-muted" />
      <h2 class="text-xl font-semibold mb-2">尚無文件</h2>
      <p class="text-muted mb-6">上傳你的第一份 PDF 文件開始使用</p>
      <UButton to="/upload" icon="i-lucide-upload">
        上傳文件
      </UButton>
    </UCard>

    <!-- 文件列表 -->
    <div v-else class="space-y-4">
      <!-- 統計 -->
      <div class="flex items-center justify-between mb-4">
        <p class="text-sm text-muted">共 {{ documents.length }} 份文件</p>
        <UButton
          icon="i-lucide-refresh-cw"
          variant="ghost"
          size="sm"
          :loading="loading"
          @click="loadDocuments"
        >
          重新整理
        </UButton>
      </div>

      <!-- 文件卡片 -->
      <NuxtLink
        v-for="doc in documents"
        :key="doc.id"
        :to="`/documents/${doc.id}`"
        class="block"
      >
        <UCard
          class="hover:shadow-lg transition-shadow cursor-pointer hover:border-primary"
        >
          <div class="flex items-center gap-4">
            <!-- 圖示 -->
            <div class="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <UIcon :name="getDocTypeIcon(doc.detected_type)" class="w-6 h-6 text-primary" />
            </div>

            <!-- 資訊 -->
            <div class="flex-1 min-w-0">
              <h3 class="font-semibold truncate">{{ doc.filename }}</h3>
              <div class="flex items-center gap-3 mt-1 text-sm text-muted">
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
            </div>

            <!-- 日期和箭頭 -->
            <div class="text-right shrink-0">
              <p class="text-sm text-muted">{{ formatDate(doc.upload_time) }}</p>
              <UIcon name="i-lucide-chevron-right" class="w-5 h-5 text-muted mt-1" />
            </div>
          </div>
        </UCard>
      </NuxtLink>
    </div>
  </div>
</template>

