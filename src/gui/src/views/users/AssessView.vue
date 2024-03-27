<template>
  <div class="w-100">
    <v-infinite-scroll
      v-if="newsItems.items.length > 0"
      empty-text="All items loaded"
      color="primary"
      @load="displayMore"
    >
      <template v-for="item in newsItems.items" :key="item">
        <card-story :story="item" @refresh="refresh(item.id)" />
      </template>
      <template #loading>
        <v-progress-circular
          color="primary"
          indeterminate
          size="24"
          width="4"
          class="mr-3 mt-3 mb-5"
        />
        loading new items ...
      </template>
    </v-infinite-scroll>

    <v-row
      v-if="newsItems.items.length == 0"
      class="align-center justify-center mt-5"
    >
      <v-col cols="12">
        <v-alert
          :value="true"
          type="info"
          text="No items found. Please change your filter."
          class="mx-4 text-center text-h5"
        />
      </v-col>
      <v-col cols="6">
        <v-btn block class="mx-4" @click="resetFilter()">Reset Filter</v-btn>
      </v-col>
    </v-row>
    <assess-selection-toolbar v-if="activeSelection" />
  </div>
</template>

<script>
import CardStory from '@/components/assess/CardStory.vue'
import AssessSelectionToolbar from '@/components/assess/AssessSelectionToolbar.vue'
import { defineComponent, computed, onUnmounted, onUpdated } from 'vue'
import { useAssessStore } from '@/stores/AssessStore'
import { useFilterStore } from '@/stores/FilterStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'
import { assessHotkeys } from '@/utils/hotkeys'

export default defineComponent({
  name: 'AssessView',
  components: {
    CardStory,
    AssessSelectionToolbar
  },
  setup() {
    const assessStore = useAssessStore()
    const filterStore = useFilterStore()
    const mainStore = useMainStore()
    const { newsItems, activeSelection, loading } = storeToRefs(assessStore)
    const { appendNewsItems, clearNewsItemSelection } = assessStore

    assessHotkeys()
    const moreToLoad = computed(() => {
      const offset = filterStore.newsItemsFilter.offset
        ? parseInt(filterStore.newsItemsFilter.offset)
        : 0
      const length = offset + newsItems.value.items.length
      return length < newsItems.value.total_count
    })

    const refresh = (id) => {
      assessStore.updateStoryByID(id)
    }

    const displayMore = async ({ done }) => {
      console.debug('displayMore', loading.value)
      if (!moreToLoad.value) {
        done('empty')
        return
      }
      if (loading.value) {
        return
      }
      await appendNewsItems()
      done('ok')
    }
    const nextPage = () => {
      filterStore.nextPage()
    }

    const resetFilter = () => {
      filterStore.resetFilter()
    }
    function onTriggeredEventHandler(payload) {
      console.log(`You have pressed CMD (CTRL) + ${payload.keyString}`)
    }

    onUpdated(() => {
      mainStore.itemCountTotal = newsItems.value.total_count
      mainStore.itemCountFiltered = newsItems.value.items.length
    })

    onUnmounted(() => {
      clearNewsItemSelection()
      mainStore.itemCountTotal = 0
      mainStore.itemCountFiltered = 0
    })

    return {
      newsItems,
      moreToLoad,
      activeSelection,
      loading,
      refresh,
      nextPage,
      resetFilter,
      displayMore,
      onTriggeredEventHandler
    }
  }
})
</script>
