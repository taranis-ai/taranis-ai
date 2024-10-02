<template>
  <div class="vertical-button-group">
    <v-btn
      v-for="option in orderOptions"
      :key="option.type"
      class="vertical-button mb-1"
      :color="selectedButton === option.type ? 'primary' : 'default'"
      :prepend-icon="option.icon"
      :append-icon="activeIcon(option.type)"
      variant="text"
      @click="onButtonClick(option.type)"
    >
      {{ option.label }}
    </v-btn>
    <v-btn
      class="vertical-button mb-1"
      :color="currentSort !== 'NONE' ? 'primary' : 'default'"
      :prepend-icon="currentSortIcon"
      variant="text"
      @click="cycleSentimentSort"
    >
      {{ currentSortLabel }}
    </v-btn>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'FilterSortList',
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    orderOptions: {
      type: Array,
      default: () => [
        {
          label: 'published date',
          icon: 'mdi-calendar-range-outline',
          type: 'DATE'
        },
        {
          label: 'relevance',
          icon: 'mdi-speedometer',
          type: 'RELEVANCE'
        }
      ]
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const selectedButton = ref('')
    const buttonState = ref({})

    const onButtonClick = (button) => {
      if (selectedButton.value === button) {
        if (buttonState.value[button] === 'DESC') {
          buttonState.value[button] = 'ASC'
        } else if (buttonState.value[button] === 'ASC') {
          buttonState.value[button] = ''
          selectedButton.value = ''
        }
      } else {
        selectedButton.value = button
        buttonState.value[button] = 'DESC'
      }

      if (selectedButton.value) {
        emit(
          'update:modelValue',
          selectedButton.value + '_' + buttonState.value[button]
        )
      } else {
        emit('update:modelValue', undefined)
      }
    }

    function activeIcon(type) {
      if (selectedButton.value !== type) return ''
      return buttonState.value[type] === 'ASC'
        ? 'mdi-arrow-up'
        : buttonState.value[type] === 'DESC'
          ? 'mdi-arrow-down'
          : ''
    }

    const sentimentStates = ['POSITIVE', 'NEUTRAL', 'NEGATIVE', 'NONE']
    const currentSortIndex = ref(3) // Start with no selected state
    
    const sortIcons = {
      POSITIVE: 'mdi-emoticon-happy-outline',
      NEUTRAL: 'mdi-emoticon-neutral-outline',
      NEGATIVE: 'mdi-emoticon-sad-outline',
      NONE: 'mdi-sort'
    }

    const sortLabels = {
      POSITIVE: 'positive sentiment',
      NEUTRAL: 'neutral sentiment',
      NEGATIVE: 'negative sentiment',
      NONE: 'sentiment score'
    }

    const currentSort = ref('NONE')
    const currentSortIcon = ref(sortIcons['NONE'])
    const currentSortLabel = ref(sortLabels['NONE'])

    const cycleSentimentSort = () => {
      currentSortIndex.value = (currentSortIndex.value + 1) % sentimentStates.length
      currentSort.value = sentimentStates[currentSortIndex.value]
      currentSortIcon.value = sortIcons[currentSort.value]
      currentSortLabel.value = sortLabels[currentSort.value]

      if (currentSort.value !== 'NONE') {
        emit('update:modelValue', currentSort.value)
      } else {
        emit('update:modelValue', undefined)
      }
    }

    return {
      selectedButton,
      onButtonClick,
      activeIcon,
      currentSort,
      currentSortIcon,
      currentSortLabel,
      cycleSentimentSort
    }
  }
}
</script>
