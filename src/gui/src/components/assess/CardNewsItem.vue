<template>
  <v-card
    :ripple="false"
    elevation="3"
    :rounded="false"
    class="no-gutters align-self-stretch mb-1 news-item-card"
    :class="{
      selected: selected
    }"
    @click="toggleSelection"
  >
    <v-row>
      <v-col
        cols="12"
        sm="12"
        lg="6"
        class="d-flex flex-grow-1 mt-3 px-5 py-3 order-first"
        align-self="center"
      >
        <h2 class="news-item-title">
          {{ title }}
        </h2>
      </v-col>

      <NewsItemActions
        :news-item="newsItem"
        :story="story"
        :detail-view="detailView"
        @delete-item="deleteNewsItem"
        @open-card="openCard()"
      />
      <v-col
        cols="12"
        sm="12"
        lg="6"
        class="px-5 pb-5 order-lg-3 order-md-2"
        align-self="stretch"
      >
        <summarized-content
          :open="openSummary"
          :is_summarized="false"
          :content="description"
        />
      </v-col>
      <v-col class="px-5 pt-2 pb-3 order-4" cols="12" sm="12" lg="6">
        <news-meta-info :news-item="newsItem" />
      </v-col>
    </v-row>
  </v-card>
</template>

<script>
import SummarizedContent from '@/components/assess/card/SummarizedContent.vue'
import NewsItemActions from '@/components/assess/card/NewsItemActions.vue'
import NewsMetaInfo from '@/components/assess/card/NewsMetaInfo.vue'
import { useAssessStore } from '@/stores/AssessStore'
import { ref, computed } from 'vue'

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
    detailView: Boolean
  },
  emits: ['deleteItem', 'refresh'],
  setup(props, { emit }) {
    const viewDetails = ref(false)
    const openSummary = ref(props.detailView)
    const assessStore = useAssessStore()
    const selected = computed(() =>
      assessStore.newsItemSelection.includes(props.newsItem.id)
    )

    const description = computed(
      () =>
        props.newsItem.news_item_data?.content ||
        props.newsItem.news_item_data?.review
    )

    const openCard = () => {
      openSummary.value = !openSummary.value
    }

    const title = computed(() => props.newsItem.news_item_data?.title)

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
    }
  }
}
</script>

<style scoped lang="scss">
.news-item-card {
  border: 2px solid white;
  &:hover {
    transition: border-color 180ms;
    border-color: color-mix(
      in srgb,
      rgb(var(--v-theme-secondary)) 50%,
      #ffffff
    );
  }
  &.selected {
    // background-color: #c3b66c;
    background-color: color-mix(
      in srgb,
      rgb(var(--v-theme-secondary)) 5%,
      #ffffff
    );
    border-color: rgb(var(--v-theme-secondary));
  }
}
</style>
