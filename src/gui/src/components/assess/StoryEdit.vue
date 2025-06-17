<template>
  <v-container fluid>
    <div v-if="hasRtId" class="alert">
      <v-icon color="error">mdi-alert-circle</v-icon>
      <span class="alert-text">
        <strong>
          This is a story from RT, you should not be editing it in this web
          insterface, but in RT itself.
        </strong>
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

          <attributes-table
            v-model="story.attributes"
            :filter-attributes="true"
          >
          </attributes-table>

          <v-spacer class="pt-1"></v-spacer>
          <div class="d-flex justify-content-start mt-5">
            <v-btn
              class="w-25"
              type="submit"
              :color="submitBtnColor"
              :disabled="hasRtId"
              :prepend-icon="submitBtnIcon"
              :text="$t('button.update')"
            />
            <v-btn
              class="ml-3 w-25"
              :to="{ name: 'story', params: { storyId: story.id } }"
              color="error"
              text="Go Back"
              data-testid="story-go-back-btn"
            />
          </div>
        </v-form>
      </v-card-text>
    </v-card>
    <div class="my-5">
      <v-card v-if="showAdvancedOptions">
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
                text="AI Based Cybersecurity Classification"
                @click="triggerCyberSecClassifierBot"
              />
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
            <cyber-security-buttons
              :news_item="news_item"
              :dirty="dirty"
              @updated="fetchStoryData()"
            />
          </v-card-text>
        </v-card>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { patchStory, triggerBot } from '@/api/assess'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import CodeEditor from '@/components/common/CodeEditor.vue'
import EditTags from '@/components/assess/EditTags.vue'
import CyberSecurityButtons from '@/components/assess/CyberSecurityButtons.vue'
import AttributesTable from '@/components/common/AttributesTable.vue'
import StoryLinks from '@/components/assess/StoryLinks.vue'
import { useUserStore } from '@/stores/UserStore'
import { useAssessStore } from '@/stores/AssessStore'
import { isEqual } from 'lodash-es'

export default {
  name: 'StoryEdit',
  components: {
    CodeEditor,
    EditTags,
    StoryLinks,
    AttributesTable,
    CyberSecurityButtons
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
    const assessStore = useAssessStore()
    const form = ref(null)
    const story = ref(JSON.parse(JSON.stringify(props.storyProp)))
    const originalStory = ref(JSON.parse(JSON.stringify(props.storyProp)))
    const dirty = ref(false)

    const showAdvancedOptions = computed(() => {
      return userStore.advanced_story_options
    })

    const news_item_ids = computed(() => {
      return story.value.news_items.map((item) => item.id)
    })

    const submitBtnColor = computed(() => {
      if (hasRtId.value) {
        return 'error'
      }
      return dirty.value ? 'warning' : 'success'
    })

    const submitBtnIcon = computed(() => {
      if (hasRtId.value) {
        return 'mdi-alert-circle'
      }
      return dirty.value ? 'mdi-alert' : 'mdi-check'
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
        story.value.attributes?.find((attr) => attr.key === 'cybersecurity')
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

    const rules = {
      required: (v) => !!v || 'Required'
    }

    function validateTLP(attributes) {
      if (!attributes) {
        return true
      }
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
      console.debug(`Submitting story: ${JSON.stringify(story.value)}`)
      const { valid } = await form.value.validate()

      if (!valid) {
        return
      }

      if (!validateTLP(story.value?.attributes)) {
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
        await fetchStoryData()
      } catch (e) {
        notifyFailure(e)
      }
    }

    async function triggerSummaryBot() {
      try {
        const result = await triggerBot('summary_bot', props.storyProp.id)
        notifySuccess(result.data.message)
      } catch (e) {
        notifyFailure(e)
      }
    }

    async function fetchStoryData() {
      try {
        const result = await assessStore.updateStoryByID(props.storyProp.id)
        originalStory.value = JSON.parse(JSON.stringify(result))
        story.value = JSON.parse(JSON.stringify(result))
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
        await fetchStoryData()
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
        await fetchStoryData()
      } catch (e) {
        notifyFailure(e)
      }
    }

    watch(
      () => story.value,
      (newStory) => {
        dirty.value = !isEqual(newStory, originalStory.value)
      },
      { deep: true, immediate: true }
    )

    return {
      showAdvancedOptions,
      news_item_ids,
      story,
      dirty,
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
      fetchStoryData,
      getChipCybersecurityClass,
      submitBtnColor,
      submitBtnIcon
    }
  }
}
</script>

<style scoped>
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
