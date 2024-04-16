<template>
  <div class="w-100">
    <v-infinite-scroll
      v-if="stories.total_count > 0 && !pagination"
      empty-text="All items loaded"
      color="primary"
      @load="displayMore"
    >
      <template v-for="item in stories.items" :key="item">
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

    <v-container v-else-if="stories.total_count > 0 && pagination" fluid>
      <template v-for="item in stories.items" :key="item">
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
      v-if="stories.total_count == 0"
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
    <assess-selection-toolbar />
  </div>
</template>

<script>
import CardStory from '@/components/assess/CardStory.vue'
import AssessSelectionToolbar from '@/components/assess/AssessSelectionToolbar.vue'
import { defineComponent, computed, onDeactivated, onUpdated } from 'vue'
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
    const { stories, loading } = storeToRefs(assessStore)
    const { storyFilter } = storeToRefs(filterStore)

    assessHotkeys()
    const moreToLoad = computed(() => {
      const offset = storyFilter.value.offset
        ? parseInt(storyFilter.value.offset)
        : 0
      const length = offset + stories.value.items.length
      return length < stories.value.total_count
    })

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
        stories.value.total_count / (storyFilter.value.limit || 20)
      )
      return count > 0 ? count : 1
    })

    const refresh = (id) => {
      assessStore.updateStoryByID(id)
    }

    const pagination = computed(() => {
      return Boolean(storyFilter.value.timeto)
    })

    const displayMore = async ({ done }) => {
      console.debug('displayMore', loading.value)
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
      done('empty')
    }

    const resetFilter = () => {
      filterStore.resetFilter()
    }
    function onTriggeredEventHandler(payload) {
      console.log(`You have pressed CMD (CTRL) + ${payload.keyString}`)
    }

    onUpdated(() => {
      mainStore.itemCountTotal = stories.value.total_count
      mainStore.itemCountFiltered = stories.value.items.length
    })

    onDeactivated(() => {
      assessStore.clearSelection()
      mainStore.itemCountTotal = 0
      mainStore.itemCountFiltered = 0
    })

    return {
      stories,
      moreToLoad,
      numberOfPages,
      page,
      loading,
      pagination,
      storyFilter,
      refresh,
      resetFilter,
      displayMore,
      onTriggeredEventHandler
    }
  }
})
</script>
