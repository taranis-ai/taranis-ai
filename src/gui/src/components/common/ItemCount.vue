<template>
  <span v-if="showCount">
    {{ itemCountText }} / displayed: {{ itemFilteredText }}
    <v-tooltip v-if="showAssessTooltip" activator="parent" location="bottom">
      <v-icon icon="mdi-eye-check-outline" size="x-small" class="mr-1" />
      read: <strong>{{ storyCounts.read_count }}</strong
      ><br />
      <!-- <v-icon icon="mdi-eye-off-outline" size="x-small" class="mr-1" />
        unread: <strong>{{ itemCountUnread }}</strong>
        <br /> -->
      <v-icon icon="mdi-star-check-outline" size="x-small" class="mr-1" />
      important: <strong>{{ storyCounts.important_count }}</strong>
      <br />
      <v-icon
        icon="mdi-google-circles-communities"
        size="x-small"
        class="mr-1"
      />
      in report: <strong>{{ storyCounts.in_reports_count }}</strong>
      <br />
    </v-tooltip>
  </span>
</template>

<script>
import { storeToRefs } from 'pinia'
import { useMainStore } from '@/stores/MainStore'
import { useAssessStore } from '@/stores/AssessStore'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { usePublishStore } from '@/stores/PublishStore'
import { defineComponent, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'

export default defineComponent({
  name: 'ItemCount',
  setup() {
    const mainStore = useMainStore()
    const assessStore = useAssessStore()
    const route = useRoute()
    const { mdAndUp } = useDisplay()

    const { storyCounts } = storeToRefs(assessStore)

    const itemCountText = computed(() => {
      if (route.name === 'assess') {
        return `total stories: ${storyCounts.value.total_count}`
      }
      if (route.name === 'analyze') {
        return `total reports: ${useAnalyzeStore().report_items.total_count}`
      }
      if (route.name === 'publish') {
        return `total products: ${usePublishStore().products.total_count}`
      }
      return `total items: ${mainStore.itemCountTotal}`
    })

    const itemFilteredText = computed(() => {
      if (route.name === 'assess') {
        return assessStore.stories.items.length
      }
      if (route.name === 'analyze') {
        return useAnalyzeStore().report_items.items.length
      }
      if (route.name === 'publish') {
        return usePublishStore().products.items.length
      }

      return mainStore.itemCountFiltered
    })

    const showAssessTooltip = computed(() => {
      return route.name === 'assess'
    })

    const showCount = computed(() => {
      return itemFilteredText.value > 0 && mdAndUp
    })

    return {
      showCount,
      itemCountText,
      storyCounts,
      itemFilteredText,
      showAssessTooltip
    }
  }
})
</script>

<style scoped>
.menu-item-info {
  cursor: help;
}
</style>
