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
            v-model="story.attributes"
            :filter-attributes="true"
            :disabled="hasRtId"
          >
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
    <div class="my-5">
      <v-card v-if="userStore.advanced_story_options">
        <v-card-title>
          <h3>AI Actions</h3>
        </v-card-title>

        <v-card-text>
          <!-- Summary row -->
          <v-row no-gutters align="center" class="mb-4">
            <v-col cols="auto">
              <v-btn
                class="equal-width-btn"
                prepend-icon="mdi-auto-fix"
                text
                @click="triggerSummaryBot"
              >
                AI Based Summary
              </v-btn>
            </v-col>
          </v-row>

          <!-- Sentiment row -->
          <v-row no-gutters align="center" class="mb-4">
            <v-col cols="auto">
              <v-btn
                class="equal-width-btn"
                prepend-icon="mdi-pulse"
                text
                @click="triggerSentimentAnalysisBot"
              >
                AI Based Sentiment Analysis
              </v-btn>
            </v-col>

            <div class="d-flex flex-wrap ml-4" style="gap: 8px">
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
          </v-row>

          <!-- Cyber-sec row -->
          <v-row no-gutters align="center" class="mb-4">
            <v-col cols="auto">
              <v-btn
                class="equal-width-btn"
                prepend-icon="mdi-shield-outline"
                text
                @click="triggerCyberSecClassifierBot"
              >
                AI Based Cybersecurity Classification
              </v-btn>
            </v-col>

            <v-chip
              class="ml-4"
              :class="getChipCybersecurityClass(storyCyberSecStatus)"
              label
              data-testid="story-cybersec-status-chip"
            >
              {{ storyCyberSecStatus }}
            </v-chip>
          </v-row>
        </v-card-text>
      </v-card>
    </div>
    <v-card>
      <v-card-title>
        <h3>News Items</h3>
      </v-card-title>

      <v-card-text>
        <v-card
          v-for="news_item in story.news_items"
          :key="news_item.id"
          :title="news_item.title"
          :value="news_item.id"
        >
          <v-card-title>
            <router-link
              :to="{ name: 'newsitem', params: { itemId: news_item.id } }"
            >
              {{ news_item.content || news_item.title }}
            </router-link>
          </v-card-title>
          <v-card-text>
            <v-row class="ms-4 px-4" align="center" justify="start" wrap>
              <v-col cols="2" class="d-flex align-center">
                <div class="d-flex justify-center pt-2">
                  <v-btn-toggle
                    v-if="userStore.advanced_story_options"
                    class="d-flex justify-center"
                    mandatory
                  >
                    <v-btn
                      value="yes"
                      :class="[
                        getButtonCybersecurityClass(news_item, 'yes'),
                        'me-2'
                      ]"
                      @click="setNewsItemCyberSecStatus(news_item, 'yes')"
                      :data-testid="`news-item-${news_item.id}-cybersec-yes-btn`"
                      text="Cybersecurity"
                    />
                    <v-btn
                      value="no"
                      :class="getButtonCybersecurityClass(news_item, 'no')"
                      @click="setNewsItemCyberSecStatus(news_item, 'no')"
                      :data-testid="`news-item-${news_item.id}-cybersec-no-btn`"
                      text="Not Cybersecurity"
                    />
                  </v-btn-toggle>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-card-text>
    </v-card>
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
    const dirty = ref(false)

    const news_item_ids = computed(() => {
      return story.value.news_items.map((item) => item.id)
    })

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

    const storyCyberSecStatus = computed(() => {
      const value =
        story.value.attributes.find((attr) => attr.key === 'cybersecurity')
          ?.value || 'Not Classified'
      return value.charAt(0).toUpperCase() + value.slice(1)
    })

    const getChipCybersecurityClass = (cybersecurity_status) => {
      switch (cybersecurity_status) {
        case 'Yes':
          return 'cyber-chip-yes'
        case 'No':
          return 'cyber-chip-no'
        case 'Mixed':
          return 'cyber-chip-mixed'
        case 'Not Classified':
          return 'cyber-chip-not-classified'
        case 'Incomplete':
          return 'cyber-chip-incomplete'
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

    function validateTLP(attributes) {
      const tlpAttr = attributes.find((attr) => attr.key === 'TLP')?.value
      if (!tlpAttr) {
        return true
      }
      const validTlpValues = ['clear', 'green', 'amber', 'amber+strict', 'red']
      if (validTlpValues.includes(tlpAttr)) {
        return true
      } else {
        notifyFailure(`Invalid TLP value: ${JSON.stringify(tlpAttr)}`)
        return false
      }
    }

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

      if (!validateTLP(story.value.attributes)) {
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

      if (!valid || dirty.value) {
        // Notify user to save changes before classifying
        notifyFailure('Please save your changes before classifying.')
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
        fetchStoryData(props.storyProp.id)
        notifySuccess(result)
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
        dirty.value =
          JSON.stringify(newStory) !== JSON.stringify(props.storyProp)
      },
      { deep: true }
    )

    watch(
      () => props.storyProp,
      (newStory) => {
        story.value = newStory
        dirty.value = false
      },
      { deep: true }
    )

    return {
      userStore,
      news_item_ids,
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
      storyCyberSecStatus,
      getChipCybersecurityClass,
      getButtonCybersecurityClass,
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

.cyber-chip-mixed {
  background-color: #9066df;
  color: white;
}

.cyber-chip-not-classified {
  background-color: #f3f3f3;
  color: black;
}

.cyber-chip-incomplete {
  background-color: #ffc107;
  color: black;
}

.equal-width-btn {
  width: 350px;
  white-space: normal;
  text-align: center;
}
</style>
