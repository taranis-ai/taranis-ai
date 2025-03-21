<template>
  <v-card
    :ripple="false"
    elevation="3"
    :rounded="false"
    class="no-gutters align-self-stretch ma-2 mb-0 news-item-card"
    :class="{
      selected: selected
    }"
    @click="toggleSelection"
  >
    <v-container
      fluid
      style="min-height: 100px"
      class="pa-0 pl-0"
      :data-testid="`news-item-card-${newsItem.id}`"
    >
      <v-row class="pl-2">
        <v-col class="d-flex">
          <v-row class="py-1 px-1">
            <v-col
              :cols="meta_cols"
              class="meta-info-col mr-n1"
              :class="smAndDown ? 'no-border' : ''"
            >
              <news-meta-info :news-item="newsItem" />
            </v-col>
            <v-col class="mr-1">
              <div class="d-flex pa-0">
                <h2
                  v-dompurify-html="title"
                  class="mb-1 mt-0 news-item-title"
                />
              </div>

              <summarized-content
                :open="openSummary"
                :is_summarized="false"
                :content="description"
              />
            </v-col>
          </v-row>
        </v-col>
        <v-col class="action-bar mr-1">
          <NewsItemActions
            :news-item="newsItem"
            :story="story"
            :detail-view="detailView"
            @delete-item="deleteNewsItem"
            @open-card="openCard()"
          />
        </v-col>
      </v-row>
    </v-container>
  </v-card>
</template>

<script>
import SummarizedContent from '@/components/assess/card/SummarizedContent.vue'
import NewsItemActions from '@/components/assess/card/NewsItemActions.vue'
import NewsMetaInfo from '@/components/assess/card/NewsMetaInfo.vue'
import { useAssessStore } from '@/stores/AssessStore'
import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useFilterStore } from '@/stores/FilterStore'
import { useDisplay } from 'vuetify'

export default {
  name: 'CardNewsItem',
  components: {
    NewsMetaInfo,
    NewsItemActions,
    SummarizedContent
  },
  props: {
    newsItem: {
      type: Object,
      required: true
    },
    story: {
      type: Object,
      required: false,
      default: null
    },
    detailView: Boolean,
    openView: Boolean
  },
  emits: ['deleteItem', 'refresh'],
  setup(props, { emit }) {
    const viewDetails = ref(false)
    const openSummary = ref(props.detailView)
    const assessStore = useAssessStore()
    const selected = computed(() =>
      assessStore.newsItemSelection.includes(props.newsItem.id)
    )
    const { compactView } = storeToRefs(useFilterStore())
    const { mdAndDown, smAndDown } = useDisplay()

    const description = computed(
      () => props.newsItem?.content || props.newsItem?.review
    )

    const content_cols = computed(() => {
      if (smAndDown.value) {
        return 12
      }
      return 10
    })

    const meta_cols = computed(() => {
      if (smAndDown.value) {
        return 12
      }
      if (compactView.value && !mdAndDown.value) {
        return 1
      }
      return 12 - content_cols.value
    })

    const openCard = () => {
      openSummary.value = !openSummary.value
    }

    const title = computed(() => props.newsItem?.title)

    const toggleSelection = () => {
      assessStore.selectNewsItem(props.newsItem.id)
    }

    const deleteNewsItem = () => {
      emit('deleteItem', props.newsItem.id)
    }

    return {
      title,
      selected,
      viewDetails,
      openSummary,
      description,
      openCard,
      toggleSelection,
      deleteNewsItem,
      meta_cols,
      content_cols,
      smAndDown
    }
  }
}
</script>

<style scoped lang="scss">
.news-item-card {
  border: 2px solid white;
  &.selected {
    background-color: color-mix(
      in srgb,
      rgb(var(--v-theme-secondary)) 5%,
      #ffffff
    );
    border-color: rgb(var(--v-theme-secondary));
  }
}

.meta-info-col {
  min-width: 240px !important;
  &.no-border {
    border-right: 0;
  }
}
</style>
