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
</script>

<template>
  <UApp>
    <UHeader>
      <template #left>
        <NuxtLink to="/" class="flex items-center gap-2">
          <UIcon name="i-lucide-scan-text" class="w-8 h-8 text-primary" />
          <span class="font-bold text-lg">OCR RAG</span>
        </NuxtLink>
      </template>

      <template #center>
        <UNavigationMenu :items="navLinks" class="hidden md:flex" />
      </template>

      <template #right>
        <UColorModeButton />
      </template>
    </UHeader>

    <UMain>
      <NuxtPage />
    </UMain>

    <UFooter>
      <template #left>
        <p class="text-sm text-muted">
          OCR RAG 文件助手 • © {{ new Date().getFullYear() }}
        </p>
      </template>

      <template #right>
        <p class="text-sm text-muted">
          Powered by Vertex AI Gemini
        </p>
      </template>
    </UFooter>
  </UApp>
</template>
