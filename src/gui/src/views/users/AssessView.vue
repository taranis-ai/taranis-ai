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
          :selected="newsItemsSelection.includes(item.id)"
          @delete-item="removeAndDeleteNewsItem(item.id)"
          @select-item="selectNewsItem(item.id)"
        />
      </template>
    </v-infinite-scroll>

    <div
      v-if="newsItems.items.length == 0"
      class="text-subtitle-1 text-center dark-grey--text mt-3"
    >
      <v-btn @click="resetFilter()">Reset Filter</v-btn>
    </div>

    <assess-selection-toolbar
      v-if="activeSelection"
      :selection="newsItemsSelection"
    ></assess-selection-toolbar>
  </div>
</template>

<script>
import CardStory from '@/components/assess/CardStory.vue'
import AssessSelectionToolbar from '@/components/assess/AssessSelectionToolbar.vue'
import { storeToRefs } from 'pinia'
import { useAssessStore } from '@/stores/AssessStore'
import { defineComponent, computed, ref, onUnmounted, onUpdated } from 'vue'
import { useFilterStore } from '@/stores/FilterStore'
import { useMainStore } from '@/stores/MainStore'

export default defineComponent({
  name: 'AssessView',
  components: {
    CardStory,
    AssessSelectionToolbar
  },
  setup() {
    const reloading = ref(false)
    const assessStore = useAssessStore()
    const filterStore = useFilterStore()
    const mainStore = useMainStore()
    const { newsItems, newsItemsSelection } = storeToRefs(assessStore)
    const { updateNewsItems, selectNewsItem, clearNewsItemSelection } =
      assessStore

    const moreToLoad = computed(() => {
      const offset = filterStore.newsItemsFilter.offset
        ? parseInt(filterStore.newsItemsFilter.offset)
        : 0
      const length = offset + newsItems.value.items.length
      return length < newsItems.value.total_count
    })

    const activeSelection = computed(() => {
      return newsItemsSelection.value.length > 0
    })

    const removeAndDeleteNewsItem = () => {
      updateNewsItems()
    }

    const displayMore = ({ done }) => {
      setTimeout(() => {
        if (!moreToLoad.value) {
          done('empty')
          return
        }
        console.debug('loading more items')
        filterStore.displayMore()
        window.scrollBy(0, -300)
        done('ok')
      }, 500)
    }

    const nextPage = () => {
      console.debug('loadNext')
      filterStore.nextPage()
      updateNewsItems()
    }

    const resetFilter = () => {
      filterStore.$reset()
      updateNewsItems()
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
      reloading,
      newsItems,
      newsItemsSelection,
      moreToLoad,
      activeSelection,
      removeAndDeleteNewsItem,
      nextPage,
      resetFilter,
      selectNewsItem,
      displayMore
    }
  }
})
</script>
