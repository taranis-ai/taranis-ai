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
    <v-row
      v-if="story && userStore.advanced_story_options"
      class="mt-4 px-4"
      align="center"
      justify="start"
      wrap
    >
      <v-col
        cols="12"
        sm="6"
        md="4"
        class="d-flex align-center"
        style="gap: 24px"
      >
        <v-btn
          prepend-icon="mdi-pulse"
          @click="triggerSentimentAnalysisBot"
          class="text-truncate mb-2"
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
        <div class="d-flex flex-wrap" style="gap: 24px">
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

    <v-row
      v-if="story && userStore.advanced_story_options"
      class="mb-4 px-4"
      align="center"
      justify="start"
      wrap
    >
      <v-col
        cols="12"
        sm="6"
        md="6"
        class="d-flex align-center"
        style="gap: 24px"
      >
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
        <v-chip
          :key="storyCyberSecStatus"
          :class="getChipCybersecurityClass(storyCyberSecStatus)"
          label
        >
          {{ storyCyberSecStatus }}
        </v-chip>
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
        <v-row class="mb-2 px-4" align="center">
          <v-col cols="2" md="2">
            <div class="d-flex justify-center pt-2">
              <v-btn-toggle
                v-if="userStore.advanced_story_options"
                class="d-flex justify-center"
                mandatory
              >
                <v-btn
                  value="yes"
                  :class="getButtonCybersecurityClass(news_item, 'yes')"
                  @click="setNewsItemCyberSecStatus(news_item, 'yes')"
                >
                  Cybersecurity
                </v-btn>

                <v-btn
                  value="no"
                  :class="getButtonCybersecurityClass(news_item, 'no')"
                  @click="setNewsItemCyberSecStatus(news_item, 'no')"
                >
                  Not Cybersecurity
                </v-btn>
              </v-btn-toggle>
            </div>
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
  updateStory,
  triggerBot,
  getStory
} from '@/api/assess'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import CodeEditor from '@/components/common/CodeEditor.vue'
import EditTags from '@/components/assess/EditTags.vue'
import AttributesTable from '@/components/common/AttributesTable.vue'
import StoryLinks from '@/components/assess/StoryLinks.vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/UserStore'

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
    const userStore = useUserStore()
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

    function getStoryCyberSecStatus(story) {
      if (!story.value?.news_items) return {}

      const counts = story.value.news_items.reduce(
        (acc, newsItem) => {
          const news_item_status = getNewsItemCyberSecStatus(newsItem)
          if (['yes_human', 'yes_bot'].includes(news_item_status)) {
            acc['yes']++
          } else if (['no_human', 'no_bot'].includes(news_item_status)) {
            acc['no']++
          }
          return acc
        },
        { yes: 0, no: 0 }
      )
      if (counts.yes && counts.no) return 'Mixed'
      if (counts.yes) return 'Yes'
      if (counts.no) return 'No'
      return 'Not Classifed'
    }

    const storyCyberSecStatus = computed(() => {
      return getStoryCyberSecStatus(story)
    })

    const getChipCybersecurityClass = (cybersecurity_status) => {
      switch (cybersecurity_status) {
        case 'Yes':
          return 'cyber-chip-yes'
        case 'No':
          return 'cyber-chip-no'
        case 'Not Classified':
          return 'cyber-chip-not-classified'
        default:
          return ''
      }
    }

    const getButtonCybersecurityClass = (news_item, button_type) => {
      const news_item_status = getNewsItemCyberSecStatus(news_item)

      if (button_type === 'yes') {
        if (news_item_status === 'yes_human') {
          return 'cybersecurity-human-btn'
        } else if (news_item_status === 'yes_bot') {
          return 'cybersecurity-bot-btn'
        } else return 'inactive-yes-btn'
      }

      if (button_type === 'no') {
        if (news_item_status === 'no_human') {
          return 'non-cybersecurity-human-btn'
        } else if (news_item_status === 'no_bot') {
          return 'non-cybersecurity-bot-btn'
        } else return 'inactive-no-btn'
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

    async function setNewsItemCyberSecStatus(news_item, status) {
      const { valid } = await form.value.validate()

      if (!valid) {
        return
      }

      // check if button should be clickable at all
      if (
        news_item?.attributes !== undefined &&
        news_item.attributes.some(
          (obj) => obj.key === 'cybersecurity_human' && obj.value === status
        )
      ) {
        return
      }

      const new_attributes = [{ key: 'cybersecurity_human', value: status }]

      try {
        if (!Array.isArray(news_item.attributes)) {
          news_item.attributes = []
        }

        const updatedKeys = new Set()

        // update attributes directly in browser
        news_item.attributes.forEach((attr) => {
          if (attr.key === 'cybersecurity_human') {
            attr.value = status
            updatedKeys.add('cybersecurity_human')
          }
        })

        if (!updatedKeys.has('cybersecurity_human')) {
          news_item.attributes.push({
            key: 'cybersecurity_human',
            value: status
          })
        }

        // update attributes in DB
        const result = await updateNewsItemAttributes(
          news_item.id,
          new_attributes
        )
        notifySuccess(result)
      } catch (e) {
        notifyFailure(e)
      }
      try {
        updateStory(story.value.id, {}, null)
      } catch (e) {
        notifyFailure(e)
      }
    }

    function getNewsItemCyberSecStatus(news_item) {
      try {
        if (!news_item || !Array.isArray(news_item.attributes)) {
          return null
        }

        const human_class = news_item.attributes.find(
          (attr) => attr.key === 'cybersecurity_human'
        )
        if (human_class?.value !== undefined)
          return human_class.value + '_human'

        const bot_class = news_item.attributes.find(
          (attr) => attr.key === 'cybersecurity_bot'
        )
        return bot_class?.value + '_bot' ?? null
      } catch (err) {
        console.error('Error in getNewsItemCyberSecStatus:', err)
        return null
      }
    }

    onMounted(() => {
      fetchStoryData(props.storyProp.id)
      userStore.loadUserProfile()
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
      userStore,
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
      getStoryCyberSecStatus,
      storyCyberSecStatus,
      getChipCybersecurityClass,
      getButtonCybersecurityClass,
      filteredStoryAttributes,
      showallattributes,
      setNewsItemCyberSecStatus,
      getNewsItemCyberSecStatus
    }
  }
}
</script>

<style scoped>
.cybersecurity-human-btn {
  background-color: #4caf50 !important;
  color: white !important;
}

.cybersecurity-bot-btn {
  background-color: #b1f3b3 !important;
  color: white !important;
}
.cybersecurity-bot-btn:hover {
  background-color: #67c46a !important;
  color: white !important;
}

.non-cybersecurity-human-btn {
  background-color: #e42e2e !important;
  color: white !important;
}

.non-cybersecurity-bot-btn {
  background-color: #faaeae !important;
  color: white !important;
}

.non-cybersecurity-bot-btn:hover {
  background-color: #e66363 !important;
  color: white !important;
}

.inactive-yes-btn {
  background-color: #f3f3f3 !important;
  color: #424242 !important;
}
.inactive-yes-btn:hover {
  background-color: #b1f3b3 !important;
  color: #424242 !important;
}

.inactive-no-btn {
  background-color: #f3f3f3 !important;
  color: #424242 !important;
}
.inactive-no-btn:hover {
  background-color: #faaeae !important;
  color: #424242 !important;
}

.cyber-chip-yes {
  background-color: #4caf50;
  color: white;
}

.cyber-chip-no {
  background-color: #e42e2e;
  color: white;
}

.cyber-chip-not-classified {
  background-color: #f3f3f3;
  color: black;
}
</style>
