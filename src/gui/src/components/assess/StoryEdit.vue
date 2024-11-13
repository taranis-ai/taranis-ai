<template>
  <v-container fluid>
    <v-card>
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
            :rules="[rules.required]"
          />
          <code-editor
            v-model:content="story.summary"
            :header="$t('enter.summary')"
            :placeholder="$t('enter.summary_placeholder')"
          />
          <v-row>
            <v-col cols="auto">
              <v-btn
                prepend-icon="mdi-auto-fix"
                text="AI based summary"
                @click="triggerSummaryBot"
              />
            </v-col>
          </v-row>
          <code-editor
            v-model:content="story.comments"
            :header="$t('enter.comment')"
            :placeholder="$t('enter.comment_placeholder')"
          />

          <edit-tags v-model="story.tags" />

          <attributes-table v-model="filteredStoryAttributes">
            <template #top>
              <v-btn
                class="mt-4"
                density="compact"
                text="show all attributes"
                @click="showallattributes = true"
              />
            </template>
          </attributes-table>
          <story-links v-model="story.links" :news-items="story.news_items" />

          <v-spacer class="pt-1"></v-spacer>
          <v-btn block class="mt-5" type="submit" color="success">
            {{ $t('button.update') }}
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
    <v-row v-if="story" class="my-2" align="center" justify="start" wrap>
      <v-col cols="12" sm="6" md="4" class="d-flex justify-center mb-2">
        <v-btn
          prepend-icon="mdi-pulse"
          @click="triggerSentimentAnalysisBot"
          class="text-truncate"
          style="width: 100%; max-width: 240px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
        >
          AI Based Sentiment Analysis
        </v-btn>
      </v-col>
      <v-col cols="12" sm="6" md="4" class="d-flex justify-center">
        <v-text-field
          :value="storySentiment"
          density="dense"
          readonly
          class="text-truncate"
          style="width: 100%; max-width: 240px; height: 36px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 0;"
        />
      </v-col>
    </v-row>
    <v-expansion-panels v-if="story" v-model="panels" multiple>
      <v-expansion-panel
        v-for="news_item in story.news_items"
        :key="news_item.id"
        :title="news_item.title"
        :value="news_item.id"
      >
        <template #text>
          <router-link
            :to="{
              name: 'newsitem',
              params: { itemId: news_item.id }
            }"
            class="d-flex fill-height align-center text-decoration-none"
            >{{ news_item.content }}
          </router-link>
        </template>
      </v-expansion-panel>
    </v-expansion-panels>
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
    const panels = ref(story.value.news_items ? story.value.news_items.map((item) => item.id) : [])
    const showallattributes = ref(false)

    const storySentiment = computed(() => {
      if (!story.value || !story.value.news_items || story.value.news_items.length === 0) {
        return 'Sentiment: Not available'
      }

      // Find the news item with valid sentiment analysis
      const sentimentNewsItem = story.value.news_items.find(
        (item) => item.attributes && item.attributes.some((attr) => attr.key === 'sentiment_score')
      );

      if (!sentimentNewsItem || !sentimentNewsItem.attributes) {
        return 'Sentiment: Not available'
      }

      // Extract sentiment score and category from the found news item
      const sentimentScoreAttr = sentimentNewsItem.attributes.find((attr) => attr.key === 'sentiment_score')
      const sentimentCategoryAttr = sentimentNewsItem.attributes.find((attr) => attr.key === 'sentiment_category')

      if (!sentimentScoreAttr || !sentimentCategoryAttr) {
        return 'Sentiment: Incomplete data'
      }

      const score = parseFloat(sentimentScoreAttr.value) * 100 // Convert to percentage
      const category = sentimentCategoryAttr.value.charAt(0).toUpperCase() + sentimentCategoryAttr.value.slice(1)

      return `${score.toFixed(2)}% ${category}`
    })

    const rules = {
      required: (v) => !!v || 'Required'
    }

    const filteredStoryAttributes = computed(() => {
      if (!story.value || !story.value.attributes) {
        return []
      }
      if (showallattributes.value) {
        return story.value.attributes
      }
      return story.value.attributes.filter((attr) => {
        return (
          Object.prototype.hasOwnProperty.call(attr, 'key') &&
          attr.key !== 'sentiment' &&
          !attr.key.includes('_BOT_')
        )
      })
    })

    const storySentiment = computed(() => {
      const sentimentAttr = story.value.attributes.find(
        (attr) => attr.key === 'sentiment'
      )
      return sentimentAttr
        ? JSON.stringify(sentimentAttr.value)
        : 'Not available'
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
        console.log("Fetched story data:", response.data)
        story.value = response.data
      } catch (e) {
        console.error('Failed to fetch story data:', e)
        notifyFailure(e)
      }
    }

    async function triggerSentimentAnalysisBot() {
      try {
        const result = await triggerBot('sentiment_analysis_bot', props.storyProp.id)
        notifySuccess(result.data.message)     
        await fetchStoryData(props.storyProp.id)
      } catch (e) {
        notifyFailure(e)
      }
    }

    onMounted(() => {
      fetchStoryData(props.storyProp.id)
    })

    watch(() => story.value, (newStory) => {
      if (newStory && newStory.news_items) {
        panels.value = newStory.news_items.map((item) => item.id)
      }
    })

    return {
      panels,
      story,
      form,
      rules,
      submit,
      triggerSummaryBot,
      triggerSentimentAnalysisBot,
      storySentiment,
      filteredStoryAttributes,
      showallattributes
    }
  }
}
</script>
