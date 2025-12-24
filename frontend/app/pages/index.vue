<script setup lang="ts">
const features = [
  {
    icon: 'i-lucide-scan-text',
    title: 'PDF OCR 辨識',
    description: '上傳 PDF 文件，AI 自動辨識文字、表格、圖片等內容'
  },
  {
    icon: 'i-lucide-database',
    title: '智能儲存',
    description: '辨識結果自動存入資料庫，支援向量搜尋'
  },
  {
    icon: 'i-lucide-message-circle',
    title: 'RAG 問答',
    description: '針對已上傳的文件進行智能問答，AI 會引用來源回答'
  },
  {
    icon: 'i-lucide-zap',
    title: '快速處理',
    description: '基於 Vertex AI Gemini 2.0，大型文件自動分批處理'
  }
]
</script>

<template>
  <div>
    <!-- Hero Section -->
    <UPageHero
      title="OCR RAG 文件助手"
      description="上傳 PDF 文件，AI 自動辨識內容，並可針對文件進行智能問答"
      :links="[
        {
          label: '開始上傳',
          to: '/upload',
          icon: 'i-lucide-upload',
          size: 'xl'
        },
        {
          label: 'AI 問答',
          to: '/ask',
          icon: 'i-lucide-message-circle',
          size: 'xl',
          color: 'neutral',
          variant: 'outline'
        }
      ]"
    />

    <!-- Features Section -->
    <UPageSection
      title="功能特色"
      description="基於 Google Vertex AI 的智能文件處理系統"
    >
      <UPageGrid>
        <UPageCard
          v-for="feature in features"
          :key="feature.title"
          :icon="feature.icon"
          :title="feature.title"
          :description="feature.description"
        />
      </UPageGrid>
    </UPageSection>

    <!-- How it works -->
    <UPageSection
      title="使用流程"
      description="三個步驟，輕鬆完成文件問答"
    >
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div class="text-center">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
            <UIcon name="i-lucide-upload" class="w-8 h-8 text-primary" />
          </div>
          <h3 class="text-lg font-semibold mb-2">1. 上傳文件</h3>
          <p class="text-muted">支援 PDF 格式，拖拉或點擊上傳</p>
        </div>

        <div class="text-center">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
            <UIcon name="i-lucide-cpu" class="w-8 h-8 text-primary" />
          </div>
          <h3 class="text-lg font-semibold mb-2">2. AI 處理</h3>
          <p class="text-muted">Gemini 自動辨識文字、表格、圖片</p>
        </div>

        <div class="text-center">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
            <UIcon name="i-lucide-message-circle" class="w-8 h-8 text-primary" />
          </div>
          <h3 class="text-lg font-semibold mb-2">3. 智能問答</h3>
          <p class="text-muted">針對文件提問，AI 引用來源回答</p>
        </div>
      </div>
    </UPageSection>

    <!-- CTA -->
    <UPageSection>
      <UPageCTA
        title="開始使用 OCR RAG"
        description="上傳你的第一份 PDF 文件，體驗 AI 文件助手"
        :links="[
          {
            label: '上傳文件',
            to: '/upload',
            icon: 'i-lucide-arrow-right',
            trailing: true,
            size: 'lg'
          }
        ]"
      />
    </UPageSection>
  </div>
</template>
