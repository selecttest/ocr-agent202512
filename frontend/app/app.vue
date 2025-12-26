<script setup lang="ts">
import type { DocumentItem } from '~/composables/useApi'

useHead({
  meta: [
    { name: 'viewport', content: 'width=device-width, initial-scale=1' }
  ],
  link: [
    { rel: 'icon', href: '/favicon.ico' }
  ],
  htmlAttrs: {
    lang: 'zh-TW'
  }
})

const title = 'OCR RAG 文件助手'
const description = '上傳 PDF 文件，智能 OCR 辨識，AI 問答系統'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description
})

// 導航選單
const navLinks = [
  { label: '首頁', to: '/', icon: 'i-lucide-home' },
  { label: '上傳文件', to: '/upload', icon: 'i-lucide-upload' },
  { label: '文件列表', to: '/documents', icon: 'i-lucide-folder-open' },
  { label: 'AI 問答', to: '/ask', icon: 'i-lucide-message-circle' }
]

// 移動端選單
const isMobileMenuOpen = ref(false)
const route = useRoute()

// 路由變化時關閉選單
watch(() => route.path, () => {
  isMobileMenuOpen.value = false
})

// ========== 檔案庫功能 ==========
const { getDocuments } = useApi()
const isFileLibraryOpen = ref(false)
const fileLibraryDocuments = ref<DocumentItem[]>([])
const fileLibraryLoading = ref(false)

// 開啟檔案庫
const openFileLibrary = async () => {
  isFileLibraryOpen.value = true
  fileLibraryLoading.value = true
  try {
    fileLibraryDocuments.value = await getDocuments(50)
  } catch (e) {
    console.error('載入文件列表失敗:', e)
  } finally {
    fileLibraryLoading.value = false
  }
}

// 格式化日期
const formatDate = (dateStr: string): string => {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  } catch {
    return dateStr
  }
}
</script>

<template>
  <UApp>
    <UHeader>
      <template #left>
        <NuxtLink to="/" class="flex items-center gap-2">
          <UIcon name="i-lucide-scan-text" class="w-7 h-7 sm:w-8 sm:h-8 text-primary" />
          <span class="font-bold text-base sm:text-lg">OCR RAG</span>
        </NuxtLink>
      </template>

      <template #center>
        <UNavigationMenu :items="navLinks" class="hidden md:flex" />
      </template>

      <template #right>
        <div class="flex items-center gap-2">
          <!-- 檔案庫按鈕 -->
          <UButton
            icon="i-lucide-library"
            variant="ghost"
            size="sm"
            class="hidden sm:flex"
            @click="openFileLibrary"
          >
            <span class="hidden lg:inline">檔案庫</span>
          </UButton>
          
          <UColorModeButton />
          
          <!-- 移動端漢堡選單按鈕 -->
          <UButton
            class="md:hidden"
            :icon="isMobileMenuOpen ? 'i-lucide-x' : 'i-lucide-menu'"
            variant="ghost"
            size="sm"
            @click="isMobileMenuOpen = !isMobileMenuOpen"
          />
        </div>
      </template>
    </UHeader>

    <!-- 移動端導航選單 -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div
        v-if="isMobileMenuOpen"
        class="md:hidden fixed inset-x-0 top-14 z-50 bg-background/95 backdrop-blur-sm border-b shadow-lg"
      >
        <nav class="container mx-auto px-4 py-3">
          <div class="flex flex-col gap-1">
            <NuxtLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              class="flex items-center gap-3 px-4 py-3 rounded-lg transition-colors"
              :class="route.path === link.to
                ? 'bg-primary/10 text-primary font-medium'
                : 'hover:bg-muted/50'"
            >
              <UIcon :name="link.icon" class="w-5 h-5" />
              <span>{{ link.label }}</span>
            </NuxtLink>
          </div>
        </nav>
      </div>
    </Transition>

    <!-- 點擊遮罩關閉選單 -->
    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isMobileMenuOpen"
        class="md:hidden fixed inset-0 top-14 z-40 bg-black/20"
        @click="isMobileMenuOpen = false"
      />
    </Transition>

    <UMain>
      <NuxtPage />
    </UMain>

    <!-- 檔案庫 Modal -->
    <UModal v-model:open="isFileLibraryOpen">
      <template #content>
        <UCard class="w-full max-w-2xl">
          <template #header>
            <div class="flex items-center justify-between">
              <h2 class="text-lg font-semibold flex items-center gap-2">
                <UIcon name="i-lucide-library" class="w-5 h-5" />
                檔案庫
              </h2>
              <UButton
                icon="i-lucide-x"
                variant="ghost"
                size="sm"
                @click="isFileLibraryOpen = false"
              />
            </div>
          </template>

          <!-- 載入中 -->
          <div v-if="fileLibraryLoading" class="text-center py-8">
            <UIcon name="i-lucide-loader-2" class="w-8 h-8 mx-auto mb-3 animate-spin text-primary" />
            <p class="text-muted">載入中...</p>
          </div>

          <!-- 無文件 -->
          <div v-else-if="fileLibraryDocuments.length === 0" class="text-center py-8">
            <UIcon name="i-lucide-folder-open" class="w-12 h-12 mx-auto mb-3 text-muted" />
            <p class="text-muted mb-4">尚無文件</p>
            <UButton to="/upload" icon="i-lucide-upload" @click="isFileLibraryOpen = false">
              上傳文件
            </UButton>
          </div>

          <!-- 文件列表 -->
          <div v-else class="max-h-[60vh] overflow-y-auto space-y-2">
            <NuxtLink
              v-for="doc in fileLibraryDocuments"
              :key="doc.id"
              :to="`/documents/${doc.id}`"
              class="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
              @click="isFileLibraryOpen = false"
            >
              <div class="flex items-start gap-3">
                <UIcon name="i-lucide-file-text" class="w-8 h-8 text-primary shrink-0 mt-0.5" />
                <div class="flex-1 min-w-0">
                  <h3 class="font-medium truncate">{{ doc.filename }}</h3>
                  <div class="flex flex-wrap items-center gap-2 mt-1 text-xs text-muted">
                    <span class="flex items-center gap-1">
                      <UIcon name="i-lucide-file-type" class="w-3 h-3" />
                      {{ doc.detected_type || '未知類型' }}
                    </span>
                    <span class="flex items-center gap-1">
                      <UIcon name="i-lucide-file" class="w-3 h-3" />
                      {{ doc.total_pages }} 頁
                    </span>
                    <span class="flex items-center gap-1">
                      <UIcon name="i-lucide-calendar" class="w-3 h-3" />
                      {{ formatDate(doc.upload_time) }}
                    </span>
                  </div>
                </div>
                <UIcon name="i-lucide-chevron-right" class="w-5 h-5 text-muted shrink-0" />
              </div>
            </NuxtLink>
          </div>

          <template #footer>
            <div class="flex justify-between items-center">
              <span class="text-sm text-muted">共 {{ fileLibraryDocuments.length }} 個文件</span>
              <div class="flex gap-2">
                <UButton to="/documents" variant="outline" size="sm" @click="isFileLibraryOpen = false">
                  查看全部
                </UButton>
                <UButton to="/upload" icon="i-lucide-upload" size="sm" @click="isFileLibraryOpen = false">
                  上傳新文件
                </UButton>
              </div>
            </div>
          </template>
        </UCard>
      </template>
    </UModal>

    <UFooter class="hidden sm:block">
      <template #left>
        <p class="text-xs sm:text-sm text-muted">
          OCR RAG 文件助手 • © {{ new Date().getFullYear() }}
        </p>
      </template>

      <template #right>
        <p class="text-xs sm:text-sm text-muted">
          Powered by Vertex AI Gemini
        </p>
      </template>
    </UFooter>
  </UApp>
</template>
