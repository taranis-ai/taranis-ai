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
            :disabled="hasRtId"
          />
          <code-editor
            v-model:content="story.summary"
            :header="$t('enter.summary')"
            :placeholder="$t('enter.summary_placeholder')"
            name="summary"
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
            name="comment"
          />

          <edit-tags v-model="story.tags" />

          <attributes-table
            v-model="filteredStoryAttributes"
            :disabled="hasRtId"
          >
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
    <v-row v-if="story" class="my-2" align="center" justify="start" wrap>
      <v-col cols="12" sm="6" md="4" class="d-flex justify-center mb-2">
        <v-btn
          prepend-icon="mdi-pulse"
          @click="triggerSentimentAnalysisBot"
          class="text-truncate"
          style="
            width: 100%;
            max-width: 240px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          "
        >
          AI Based Sentiment Analysis
        </v-btn>
      </v-col>
      <v-col cols="12" sm="6" md="4" class="d-flex justify-center">
        <div class="d-flex flex-wrap" style="gap: 8px">
          <v-chip
            v-for="(count, sentiment) in sentimentCounts"
            :key="sentiment"
            :color="getSentimentColor(sentiment)"
            text-color="white"
            label
          >
            {{ sentiment.charAt(0).toUpperCase() + sentiment.slice(1) }}:
            {{ count }}
          </v-chip>
        </div>
      </v-col>
    </v-row>
    <v-row v-if="story" class="my-2" align="center" justify="start" wrap>
      <v-col cols="12" sm="6" md="4" class="d-flex justify-center mb-2">
        <v-btn
          prepend-icon="mdi-shield-outline"
          @click="triggerCyberSecClassifierBot"
          class="text-truncate"
          style="
            width: 100%;
            max-width: 240px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          "
        >
          Classify Cybersecurity
        </v-btn>
      </v-col>
      <v-col cols="12" sm="6" md="4" class="d-flex justify-center">
        <div class="d-flex flex-wrap" style="gap: 8px">
          <v-chip
            :key="cybersecurityStatus"
            :color="getCybersecurityColor(cybersecurityStatus)"
            text-color="black"
            label
          >
            {{
              cybersecurityStatus.charAt(0).toUpperCase() +
              cybersecurityStatus.slice(1)
            }}
          </v-chip>
        </div>
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
            >{{ news_item.content }}</router-link
          >
        </template>
        <v-row class="mt-4" align="center">
          <v-col cols="12" md="4">
            <span>Cybersecurity related?</span>
          </v-col>
          <v-col cols="6" md="4">
            <v-btn
              color="success"
              @click="setCyberSecurityStatus(news_item, 'yes')"
            >
              Yes
            </v-btn>
          </v-col>
          <v-col cols="6" md="4">
            <v-btn
              color="error"
              @click="setCyberSecurityStatus(news_item, 'no')"
            >
              No
            </v-btn>
          </v-col>
        </v-row>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-container>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import {
  patchStory,
  updateNewsItemAttributes,
  triggerBot,
  getStory
} from '@/api/assess'
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
    const showallattributes = ref(false)

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

    const getSentimentColor = (sentiment) => {
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

    const cybersecurityStatus = computed(() => {
      if (!story.value?.news_items) return {}

      const counts = story.value.news_items.reduce(
        (acc, newsItem) => {
          const cybersecurity_status = newsItem.attributes
            ?.find((attr) => attr.key === 'cybersecurity')
            ?.value.toLowerCase()

          if (cybersecurity_status === 'yes' || cybersecurity_status === 'no') {
            acc[cybersecurity_status]++
          }
          return acc
        },
        { yes: 0, no: 0 }
      )

      if (counts.yes && counts.no) return 'mixed'
      if (counts.yes) return 'yes'
      if (counts.no) return 'no'
      return 'not classifed'
    })

    const getCybersecurityColor = (cybersecurity_status) => {
      switch (cybersecurity_status) {
        case 'yes':
          return 'rgba(30, 144, 255, 1)'
        case 'no':
          return 'rgba(255, 69, 0, 1)'
        default:
          return 'rgba(128, 128, 128, 1)'
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

    async function triggerCyberSecClassifierBot() {
      try {
        const result = await triggerBot(
          'cybersec_classifier_bot',
          props.storyProp.id
        )
        notifySuccess(result.data.message)
        await fetchStoryData(props.storyProp.id)
      } catch (e) {
        notifyFailure(e)
      }
    }

    async function setCyberSecurityStatus(news_item, status) {
      const { valid } = await form.value.validate()

      if (!valid) {
        return
      }

      let score
      if (status == 'yes') score = 1.0
      else score = 0.0

      const new_attributes = [
        { key: 'cybersecurity', value: status },
        { key: 'cybersecurity_score', value: score }
      ]

      try {
        news_item.attributes.forEach((attr) => {
          if (attr.key === 'cybersecurity') {
            attr.value = status
          }
          if (attr.key === 'cybersecurity_score') {
            attr.value = score
          }
        })

        const result = await updateNewsItemAttributes(
          news_item.id,
          new_attributes
        )
        notifySuccess(result)
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
      triggerCyberSecClassifierBot,
      sentimentCounts,
      getSentimentColor,
      cybersecurityStatus,
      getCybersecurityColor,
      filteredStoryAttributes,
      showallattributes,
      setCyberSecurityStatus
    }
  }
}
</script>
