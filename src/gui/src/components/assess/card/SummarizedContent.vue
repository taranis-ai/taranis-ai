<template>
  <span :class="news_item_summary_class">
    <v-tooltip v-if="isSummarized" top>
      <template #activator="{ props }">
        <v-icon v-bind="props">mdi-text-short</v-icon>
      </template>
      <span>This text is Summarized</span>
    </v-tooltip>
    <span v-dompurify-html="highlighted"></span>
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
    }
  },
  setup(props) {
    const colorStart = ref(Math.floor(Math.random() * 9))

    const news_item_summary_class = computed(() => {
      return props.open ? 'news-item-summary-no-clip' : 'news-item-summary'
    })

    const highlighted = computed(() => {
      return highlight_text(props.content)
    })

    return {
      colorStart,
      news_item_summary_class,
      highlighted
    }
  }
}
</script>

<style scoped>
.news-item-summary {
  margin-bottom: 0px !important;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  line-clamp: 4;
  -webkit-box-orient: vertical;
  height: calc(1.5em * 4);
}
.news-item-summary-no-clip {
  margin-bottom: 0px !important;
  min-height: 6em;
}
</style>
