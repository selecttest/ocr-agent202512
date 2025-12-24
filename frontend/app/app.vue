<script setup>
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
