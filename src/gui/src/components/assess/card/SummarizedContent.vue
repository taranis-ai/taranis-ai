<template>
  <span :class="contentClass">
    <v-tooltip v-if="isSummarized" text="Summary">
      <template #activator="{ props }">
        <v-icon v-bind="props" icon="mdi-text-short" />
      </template>
    </v-tooltip>
    <span
      v-dompurify-html="highlighted"
      style="word-wrap: anywhere"
      data-testid="summarized-content-span"
    />
  </span>
</template>

<script>
import { ref, computed } from 'vue'
import { highlight_text } from '@/utils/helpers'

export default {
  name: 'SummarizedContent',
  props: {
    content: {
      type: String,
      default: ''
    },
    isSummarized: {
      type: Boolean,
      default: false
    },
    open: {
      type: Boolean,
      default: false
    },
    compact: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const colorStart = ref(Math.floor(Math.random() * 9))

    const highlighted = computed(() => {
      return highlight_text(props.content)
    })

    const contentClass = computed(() => {
      return props.open
        ? 'news-item-summary-no-clip'
        : props.compact
          ? 'news-item-summary-compact'
          : 'news-item-summary'
    })

    return {
      colorStart,
      highlighted,
      contentClass
    }
  }
}
</script>

<style scoped>
.news-item-summary {
  margin-bottom: 0px !important;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  line-clamp: 4;
  -webkit-box-orient: vertical;
  min-height: 1.5em;
}
.news-item-summary-compact {
  margin-bottom: 0px !important;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  min-height: 1.5em;
}
.news-item-summary-no-clip {
  display: -webkit-box;
  min-height: 1.5em;
  white-space: pre-line;
}
</style>
