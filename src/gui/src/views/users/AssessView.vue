<template>
  <div class="w-100" data-testid="all-stories-div">
    <div v-if="loading" class="d-flex justify-center align-center">
      <v-progress-circular
        color="primary"
        indeterminate
        size="64"
        width="8"
        class="mr-3 mt-3 mb-5"
      />
      loading new items ...
    </div>
    <v-infinite-scroll
      v-if="stories.items.length > 0 && infiniteScroll"
      empty-text="All items loaded"
      color="primary"
      mode="manual"
      @load="displayMore"
    >
      <template v-for="item in stories.items" :key="item.id">
        <card-story :story="item" @refresh="refresh(item.id)" />
      </template>
      <template #loading />
    </v-infinite-scroll>
    <div v-if="infiniteScroll && storySelection.length > 0" class="mb-16"></div>
    <v-container v-else-if="stories.items.length > 0 && !infiniteScroll" fluid>
      <template v-for="item in stories.items" :key="item.id">
        <card-story :story="item" @refresh="refresh(item.id)" />
      </template>
      <v-row class="justify-center mt-10 mb-10">
        <v-pagination
          v-model="page"
          :length="numberOfPages"
          :total-visible="7"
        />
      </v-row>
    </v-container>
    <v-row
      v-if="stories.items.length == 0 && !loading"
      class="align-center justify-center"
    >
      <v-col cols="12">
        <v-empty-state
          icon="mdi-magnify"
          text="Try adjusting your search terms or filters."
          title="No items match."
          class="my-5"
        />
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-btn block prepend-icon="mdi-refresh" @click="resetFilter()"
          >reset filter</v-btn
        >
      </v-col>
    </v-row>
    <assess-selection-toolbar />
  </div>
</template>

<script>
import CardStory from '@/components/assess/CardStory.vue'
import AssessSelectionToolbar from '@/components/assess/AssessSelectionToolbar.vue'
import {
  defineComponent,
  computed,
  onDeactivated,
  onActivated,
  onBeforeMount,
  watch
} from 'vue'
import { useAssessStore } from '@/stores/AssessStore'
import { useFilterStore } from '@/stores/FilterStore'
import { storeToRefs } from 'pinia'
import { assessHotkeys } from '@/utils/hotkeys'
import { updateFilterFromQuery } from '@/utils/helpers'
import { useRoute } from 'vue-router'

export default defineComponent({
  name: 'AssessView',
  components: {
    CardStory,
    AssessSelectionToolbar
  },
  setup() {
    const assessStore = useAssessStore()
    const filterStore = useFilterStore()
    const { stories, loading, storyCounts, storySelection } =
      storeToRefs(assessStore)
    const { storyFilter, storyPage, infiniteScroll } = storeToRefs(filterStore)
    console.log(storySelection)
    let doneCallback = null

    assessHotkeys()
    const page = computed({
      get: () => {
        return Number(storyFilter.value.page) + 1 || 0
      },
      set: (val) => {
        storyFilter.value.page = String(val - 1)
      }
    })
    const numberOfPages = computed(() => {
      const count = Math.ceil(
        storyCounts.value.total_count / (storyFilter.value.limit || 20)
      )
      return count > 0 ? count : 1
    })

    const moreToLoad = computed(() => {
      return storyPage.value + 1 < numberOfPages.value
    })

    function refresh(id) {
      assessStore.updateStoryByID(id)
    }

    async function displayMore({ done }) {
      console.debug(`moreToLoad: ${moreToLoad.value}`)
      doneCallback = done
      if (!moreToLoad.value) {
        done('empty')
        return
      }
      if (loading.value) {
        setTimeout(async () => {
          loading.value = false
        }, 2000)
        return
      }
      if (await assessStore.appendStories()) {
        done('ok')
      }
    }

    function resetFilter() {
      assessStore.resetFilter()
    }

    watch(storyFilter.value, () => {
      if (typeof doneCallback === 'function') {
        doneCallback('ok')
      }
    })

    onBeforeMount(() => {
      assessStore.updateStories()
    })

    onDeactivated(() => {
      assessStore.clearSelection()
    })

    onActivated(() => {
      updateFilterFromQuery(useRoute().query, 'assess')
    })

    return {
      stories,
      storySelection,
      moreToLoad,
      numberOfPages,
      infiniteScroll,
      page,
      loading,
      storyFilter,
      refresh,
      resetFilter,
      displayMore
    }
  }
})
</script>
