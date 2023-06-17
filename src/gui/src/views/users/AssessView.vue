<template>
  <div>
    <v-container fluid class="flex-column">
      <v-row v-if="!items">
        <v-col cols="12" class="empty-list-notification">
          <v-icon x-large> mdi-circle-off-outline </v-icon>
          <span v-if="items.total_count">
            The currently selected filters do not yield any results. Try
            changing the filters.
          </span>
          <span v-else> No elements to display. </span>
        </v-col>
      </v-row>

      <card-story
        v-for="newsItem in items"
        :key="newsItem.id"
        :story="newsItem"
        :selected="newsItemsSelection.includes(newsItem.id)"
        @delete-item="removeAndDeleteNewsItem(newsItem.id)"
        @select-item="selectNewsItem(newsItem.id)"
      />
    </v-container>

    <!-- TODO: Loader not working -->
    <div class="text-subtitle-1 text-center dark-grey--text mt-3">
      <div v-if="moreToLoad">
        <v-btn @click="loadNext">Next Page</v-btn>
      </div>
      <div v-else>
        <v-icon left color="primary">mdi-checkbox-marked-circle-outline</v-icon>
        All items loaded.
      </div>
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
import {
  watch,
  defineComponent,
  computed,
  ref,
  onMounted,
  onUnmounted
} from 'vue'
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
    const items = ref([])
    const assessStore = useAssessStore()
    const filterStore = useFilterStore()
    const mainStore = useMainStore()
    const { newsItems, newsItemsSelection } = storeToRefs(assessStore)
    const {
      updateNewsItems,
      selectNewsItem,
      updateOSINTSourceGroupsList,
      updateOSINTSources,
      clearNewsItemSelection
    } = assessStore

    const moreToLoad = computed(() => {
      const offset = filterStore.newsItemsFilter.offset
        ? parseInt(filterStore.newsItemsFilter.offset)
        : 0
      const length = offset + items.value.length
      return length < newsItems.value.total_count
    })

    const activeSelection = computed(() => {
      return newsItemsSelection.value.length > 0
    })

    const removeAndDeleteNewsItem = (id) => {
      items.value = items.value.filter((x) => x.id !== id)
    }

    const loadMore = ({ done }) => {
      console.debug('loadMore')
      filterStore.displayMore()
      updateNewsItems()
      done('ok')
    }

    const loadNext = ({ done }) => {
      console.debug('loadNext')
      filterStore.nextPage()
      updateNewsItems()
      done('ok')
    }

    const getNewsItemsFromStore = () => {
      items.value = newsItems.value.items
      mainStore.itemCountTotal = newsItems.value.total_count
      mainStore.itemCountFiltered = items.value.length
      console.debug('number of newsitems: ' + newsItems.value.total_count)
    }

    onMounted(() => {
      updateOSINTSourceGroupsList()
      updateOSINTSources()
      updateNewsItems()
      watch(newsItems, () => {
        getNewsItemsFromStore()
      })
    })

    onUnmounted(() => {
      clearNewsItemSelection()
      mainStore.itemCountTotal = 0
      mainStore.itemCountFiltered = 0
    })

    return {
      reloading,
      items,
      newsItemsSelection,
      moreToLoad,
      activeSelection,
      removeAndDeleteNewsItem,
      loadNext,
      selectNewsItem,
      loadMore
    }
  }
})
</script>
