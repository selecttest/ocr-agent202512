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
    <!-- Hero Section - 響應式 -->
    <section class="py-12 sm:py-16 md:py-24 px-4">
      <div class="max-w-4xl mx-auto text-center">
        <h1 class="text-3xl sm:text-4xl md:text-5xl font-bold mb-4 sm:mb-6">
          OCR RAG 文件助手
        </h1>
        <p class="text-base sm:text-lg md:text-xl text-muted mb-6 sm:mb-8 px-4">
          上傳 PDF 文件，AI 自動辨識內容，並可針對文件進行智能問答
        </p>
        <div class="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center px-4">
          <UButton
            to="/upload"
            icon="i-lucide-upload"
            size="lg"
            class="w-full sm:w-auto"
          >
            開始上傳
          </UButton>
          <UButton
            to="/ask"
            icon="i-lucide-message-circle"
            size="lg"
            color="neutral"
            variant="outline"
            class="w-full sm:w-auto"
          >
            AI 問答
          </UButton>
        </div>
      </div>
    </section>

    <!-- How it works - 響應式 -->
    <section class="how-it-works-section py-12 sm:py-16 px-4">
      <div class="text-center mb-8 sm:mb-12">
        <h2 class="text-2xl sm:text-3xl font-bold mb-2 sm:mb-4">使用流程</h2>
        <p class="text-sm sm:text-base text-muted">三個步驟，輕鬆完成文件問答</p>
      </div>

      <div class="steps-container">
        <div class="step-item">
          <div class="w-14 h-14 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-primary/10 flex items-center justify-center">
            <UIcon name="i-lucide-upload" class="w-7 h-7 sm:w-8 sm:h-8 text-primary" />
          </div>
          <h3 class="text-base sm:text-lg font-semibold mb-2">1. 上傳文件</h3>
          <p class="text-xs sm:text-sm text-muted">支援 PDF 格式，拖拉或點擊上傳</p>
        </div>

        <div class="step-item">
          <div class="w-14 h-14 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-primary/10 flex items-center justify-center">
            <UIcon name="i-lucide-cpu" class="w-7 h-7 sm:w-8 sm:h-8 text-primary" />
          </div>
          <h3 class="text-base sm:text-lg font-semibold mb-2">2. AI 處理</h3>
          <p class="text-xs sm:text-sm text-muted">Gemini 自動辨識文字、表格、圖片</p>
        </div>

        <div class="step-item">
          <div class="w-14 h-14 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-primary/10 flex items-center justify-center">
            <UIcon name="i-lucide-message-circle" class="w-7 h-7 sm:w-8 sm:h-8 text-primary" />
          </div>
          <h3 class="text-base sm:text-lg font-semibold mb-2">3. 智能問答</h3>
          <p class="text-xs sm:text-sm text-muted">針對文件提問，AI 引用來源回答</p>
        </div>
      </div>
    </section>
    
    <!-- Features Section - 響應式 -->
    <section class="py-12 sm:py-16 px-4 bg-muted/30">
      <div class="max-w-6xl mx-auto">
        <div class="text-center mb-8 sm:mb-12">
          <h2 class="text-2xl sm:text-3xl font-bold mb-2 sm:mb-4">功能特色</h2>
          <p class="text-sm sm:text-base text-muted">基於 Google Vertex AI 的智能文件處理系統</p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <UCard
            v-for="feature in features"
            :key="feature.title"
            class="text-center p-4 sm:p-6"
          >
            <div class="w-12 h-12 sm:w-14 sm:h-14 mx-auto mb-3 sm:mb-4 rounded-full bg-primary/10 flex items-center justify-center">
              <UIcon :name="feature.icon" class="w-6 h-6 sm:w-7 sm:h-7 text-primary" />
            </div>
            <h3 class="text-base sm:text-lg font-semibold mb-2">{{ feature.title }}</h3>
            <p class="text-xs sm:text-sm text-muted">{{ feature.description }}</p>
          </UCard>
        </div>
      </div>
    </section> 

    <!-- CTA - 響應式 -->
    <section class="py-12 sm:py-16 px-4 bg-primary/5">
      <div class="max-w-2xl mx-auto text-center">
        <h2 class="text-xl sm:text-2xl font-bold mb-3 sm:mb-4">開始使用 OCR RAG</h2>
        <p class="text-sm sm:text-base text-muted mb-6">上傳你的第一份 PDF 文件，體驗 AI 文件助手</p>
        <UButton
          to="/upload"
          icon="i-lucide-arrow-right"
          size="lg"
          trailing
          class="w-full sm:w-auto"
        >
          上傳文件
        </UButton>
      </div>
    </section>
  </div>
</template>
