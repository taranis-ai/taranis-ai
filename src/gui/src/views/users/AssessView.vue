<template>
  <div>
    <v-infinite-scroll
      v-if="newsItems.items.length > 0"
      empty-text="All items loaded"
      @load="displayMore"
    >
      <template v-for="item in newsItems.items" :key="item">
        <card-story
          :story="item"
          @delete-item="deleteNewsItem(item.id)"
          @refresh="refresh(item.id)"
        />
      </template>
    </v-infinite-scroll>

    <div
      v-if="newsItems.items.length == 0"
      class="text-subtitle-1 text-center dark-grey--text mt-3"
    >
      <v-btn @click="resetFilter()">Reset Filter</v-btn>
    </div>

    <assess-selection-toolbar v-if="activeSelection" />
  </div>
</template>

<script>
import CardStory from '@/components/assess/CardStory.vue'
import AssessSelectionToolbar from '@/components/assess/AssessSelectionToolbar.vue'
import { storeToRefs } from 'pinia'
import { useAssessStore } from '@/stores/AssessStore'
import { defineComponent, computed, onUnmounted, onUpdated } from 'vue'
import { useFilterStore } from '@/stores/FilterStore'
import { useMainStore } from '@/stores/MainStore'

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

    const moreToLoad = computed(() => {
      const offset = filterStore.newsItemsFilter.offset
        ? parseInt(filterStore.newsItemsFilter.offset)
        : 0
      const length = offset + newsItems.value.items.length
      return length < newsItems.value.total_count
    })

    const refresh = (id) => {
      assessStore.updateNewsItemByID(id)
    }

    const deleteNewsItem = (id) => {
      assessStore.removeNewsItemByID(id)
    }

    const displayMore = async ({ done }) => {
      console.debug('displayMore')
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
      console.debug('loadNext')
      filterStore.nextPage()
    }

    const resetFilter = () => {
      filterStore.$reset()
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
      refresh,
      nextPage,
      resetFilter,
      deleteNewsItem,
      displayMore
    }
  }
})
</script>
