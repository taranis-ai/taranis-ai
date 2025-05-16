<template>
  <v-row class="ms-4 px-4" align="center" justify="start" wrap>
    <v-col cols="2" class="d-flex align-center">
      <div class="d-flex justify-center pt-2">
        <v-btn-toggle
          v-if="showAdvancedOptions"
          class="d-flex justify-center"
          mandatory
        >
          <v-btn
            value="yes"
            :class="[getButtonCybersecurityClass(news_item, 'yes'), 'me-2']"
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
</template>

<script>
import { computed } from 'vue'
import { updateNewsItemAttributes, triggerBot } from '@/api/assess'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useUserStore } from '@/stores/UserStore'

export default {
  name: 'CyberSecurityButtons',

  props: {
    news_item: {
      type: Object,
      default: () => {},
      required: true
    },
    dirty: {
      type: Boolean,
      default: false
    }
  },
  emits: ['updated'],
  setup(props, { emit }) {
    const userStore = useUserStore()

    const showAdvancedOptions = computed(() => {
      return userStore.advanced_story_options
    })

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
      // check if button should be clickable at all
      // TODO replace this mechanism by using correct vuetify component
      if (
        news_item?.attributes !== undefined &&
        news_item.attributes.some(
          (obj) => obj.key === 'cybersecurity_human' && obj.value === status
        )
      ) {
        return
      }

      if (props.dirty) {
        // Notify user to save changes before classifying
        notifyFailure('Please save your changes before classifying.')
        return
      }

      const new_attributes = [{ key: 'cybersecurity_human', value: status }]

      try {
        await updateNewsItemAttributes(news_item.id, new_attributes)
        emit('updated', news_item.id)
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

    return {
      showAdvancedOptions,
      getButtonCybersecurityClass,
      triggerCyberSecClassifierBot,
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
</style>
