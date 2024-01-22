<template>
  <div class="w-100">
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
    <v-overlay :model-value="loading" class="align-center justify-center">
      <v-progress-circular color="primary" indeterminate size="64" />
    </v-overlay>

    <v-row
      v-if="newsItems.items.length == 0 && !loading"
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
      assessStore.updateStoryByID(id)
    }

    const deleteNewsItem = (id) => {
      assessStore.removeNewsItemByID(id)
    }

    const displayMore = async ({ done }) => {
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
      loading,
      refresh,
      nextPage,
      resetFilter,
      deleteNewsItem,
      displayMore
    }
  }
})
</script>
