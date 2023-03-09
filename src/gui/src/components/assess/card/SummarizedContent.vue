<template>
  <p :class="news_item_summary_class">
    <v-tooltip top v-if="is_summarized">
    <template v-slot:activator="{ on, attrs }">
      <v-icon v-on="on" v-bind="attrs">mdi-text-short</v-icon>
    </template>
    <span>This text is Summarized</span>
  </v-tooltip>
    {{ content }}
  </p>
</template>

<script>

export default {
  name: 'TagList',
  props: {
    content: {
      type: String,
      default: ''
    },
    is_summarized: {
      type: Boolean,
      default: false
    },
    open: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    news_item_summary_class() {
      return this.open
        ? 'news-item-summary-no-clip'
        : 'news-item-summary'
    }
  },
  data: () => ({
    colorStart: Math.floor(Math.random() * 9)
  }),
  methods: {
  }
}
</script>
