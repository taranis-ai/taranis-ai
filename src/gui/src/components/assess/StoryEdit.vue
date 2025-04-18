<template>
  <v-container fluid>
    <div v-if="hasRtId" class="alert">
      <v-icon color="error">mdi-alert-circle</v-icon>
      <span class="alert-text">
        <strong>
          This is a story from RT, you should not be editing it in this web
          insterface, but in RT itself.</strong
        >
      </span>
    </div>
    <v-card>
      <v-card-title>
        <h3>Story - {{ story.id }}</h3>
      </v-card-title>
      <v-card-text>
        <v-form
          id="form"
          ref="form"
          validate-on="submit"
          style="width: 100%; padding: 8px"
          @submit.prevent="submit"
        >
          <v-text-field
            v-model="story.title"
            :label="$t('enter.title')"
            name="title"
            type="text"
            variant="outlined"
            :rules="[rules.required]"
            :disabled="hasRtId"
          />
          <code-editor
            v-model:content="story.summary"
            :header="$t('enter.summary')"
            :placeholder="$t('enter.summary_placeholder')"
            name="summary"
          />
          <code-editor
            v-model:content="story.comments"
            :header="$t('enter.comment')"
            :placeholder="$t('enter.comment_placeholder')"
            name="comment"
          />

          <edit-tags v-model="story.tags" class="mt-3" />
          <story-links v-model="story.links" :news-items="story.news_items" />

          <!-- TODO: SHOW META INFO LIKE SENTIMENT AND TLP -->

          <attributes-table
            v-model="filteredStoryAttributes"
            :disabled="hasRtId"
          >
            <template #top>
              <v-switch
                class="mr-4"
                label="show all attributes"
                v-model="showAllAttributes"
                density="compact"
                hide-details
                color="primary"
              ></v-switch>
            </template>
          </attributes-table>

          <v-spacer class="pt-1"></v-spacer>
          <v-btn
            block
            class="mt-5"
            type="submit"
            :color="hasRtId ? 'error' : 'success'"
          >
            {{ $t('button.update') }}
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
    <v-card class="my-5">
      <v-card-title>
        <h3>AI Actions</h3>
      </v-card-title>

      <v-card-text class="d-flex">
        <v-btn
          prepend-icon="mdi-pulse"
          @click="triggerSentimentAnalysisBot"
          text="AI Based Sentiment Analysis"
        >
        </v-btn>
        <v-chip
          v-for="(count, sentiment) in sentimentCounts"
          :key="sentiment"
          :color="getColor(sentiment)"
          text-color="white"
          label
        >
          {{ sentiment.charAt(0).toUpperCase() + sentiment.slice(1) }}:
          {{ count }}
        </v-chip>
        <v-btn
          class="ml-4"
          prepend-icon="mdi-auto-fix"
          text="AI Based Summary"
          @click="triggerSummaryBot"
        />
      </v-card-text>
    </v-card>
    <v-card>
      <v-card-title>
        <h3>News Items</h3>
      </v-card-title>

      <v-card-text>
        <v-expansion-panels v-if="story" v-model="panels" multiple>
          <v-expansion-panel
            v-for="news_item in story.news_items"
            :key="news_item.id"
            :title="news_item.title"
            :value="news_item.id"
          >
            <v-expansion-panel-text>
              <router-link
                :to="{ name: 'newsitem', params: { itemId: news_item.id } }"
              >
                {{ news_item.content || news_item.title }}
              </router-link>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { patchStory, triggerBot, getStory } from '@/api/assess'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import CodeEditor from '@/components/common/CodeEditor.vue'
import EditTags from '@/components/assess/EditTags.vue'
import AttributesTable from '@/components/common/AttributesTable.vue'
import StoryLinks from '@/components/assess/StoryLinks.vue'
import { useRouter } from 'vue-router'

export default {
  name: 'StoryEdit',
  components: {
    CodeEditor,
    EditTags,
    StoryLinks,
    AttributesTable
  },
  props: {
    storyProp: {
      type: Object,
      default: () => {},
      required: true
    }
  },
  setup(props) {
    const form = ref(null)
    const router = useRouter()
    const story = ref(props.storyProp)
    const panels = ref(
      story.value.news_items
        ? story.value.news_items.map((item) => item.id)
        : []
    )
    const showAllAttributes = ref(false)

    const sentimentCounts = computed(() => {
      if (!story.value || !story.value.news_items) {
        return {}
      }

      const counts = {
        positive: 0,
        negative: 0,
        neutral: 0
      }
      story.value.news_items.forEach((newsItem) => {
        const sentimentCategoryAttr = newsItem.attributes?.find(
          (attr) => attr.key === 'sentiment_category'
        )

        if (sentimentCategoryAttr) {
          const sentiment = sentimentCategoryAttr.value.toLowerCase()
          if (counts.hasOwnProperty(sentiment)) {
            counts[sentiment]++
          }
        }
      })

      return Object.fromEntries(
        Object.entries(counts).filter(([_, count]) => count > 0)
      )
    })

    const getColor = (sentiment) => {
      switch (sentiment) {
        case 'positive':
          return 'green'
        case 'negative':
          return 'red'
        case 'neutral':
          return 'gray'
        default:
          return 'blue'
      }
    }

    const rules = {
      required: (v) => !!v || 'Required'
    }
    const filteredStoryAttributes = computed({
      get() {
        if (!story.value || !story.value.attributes) {
          return []
        }
        if (showAllAttributes.value) {
          return story.value.attributes
        }
        return story.value.attributes.filter((attr) => {
          return (
            Object.prototype.hasOwnProperty.call(attr, 'key') &&
            attr.key !== 'sentiment' &&
            !attr.key.includes('_BOT_') &&
            !attr.key === 'TLP'
          )
        })
      },
      set(newAttributes) {
        story.value.attributes = newAttributes
      }
    })

    const hasRtId = computed(() => {
      return (
        story.value?.attributes?.some((attr) => attr.key === 'rt_id') || false
      )
    })
    async function submit() {
      const { valid } = await form.value.validate()

      if (!valid) {
        return
      }

      try {
        const result = await patchStory(props.storyProp.id, {
          title: story.value.title,
          tags: story.value.tags,
          comments: story.value.comments,
          summary: story.value.summary,
          attributes: story.value.attributes,
          links: story.value.links
        })
        notifySuccess(result)
      } catch (e) {
        notifyFailure(e)
      }
      router.push('/story/' + props.storyProp.id)
    }

    async function triggerSummaryBot() {
      try {
        const result = await triggerBot('summary_bot', props.storyProp.id)
        notifySuccess(result.data.message)
      } catch (e) {
        notifyFailure(e)
      }
    }

    async function fetchStoryData(storyId) {
      try {
        const response = await getStory(storyId)
        console.log('Fetched story data:', response.data)
        story.value = response.data
      } catch (e) {
        console.error('Failed to fetch story data:', e)
        notifyFailure(e)
      }
    }

    async function triggerSentimentAnalysisBot() {
      try {
        const result = await triggerBot(
          'sentiment_analysis_bot',
          props.storyProp.id
        )
        notifySuccess(result.data.message)
        await fetchStoryData(props.storyProp.id)
      } catch (e) {
        notifyFailure(e)
      }
    }

    onMounted(() => {
      fetchStoryData(props.storyProp.id)
    })

    watch(
      () => story.value,
      (newStory) => {
        if (newStory && newStory.news_items) {
          panels.value = newStory.news_items.map((item) => item.id)
        }
      }
    )

    return {
      panels,
      story,
      hasRtId,
      form,
      rules,
      submit,
      triggerSummaryBot,
      triggerSentimentAnalysisBot,
      sentimentCounts,
      getColor,
      filteredStoryAttributes,
      showAllAttributes
    }
  }
}
</script>
