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
import { ref, watch } from 'vue'

export default {
  setup(props, { emit }) {
    const sentimentStates = ['POSITIVE', 'NEUTRAL', 'NEGATIVE', 'NONE']
    const currentSortIndex = ref(3)
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
      currentSortIndex.value =
        (currentSortIndex.value + 1) % sentimentStates.length
      currentSort.value = sentimentStates[currentSortIndex.value]
      currentSortIcon.value = sortIcons[currentSort.value]
      currentSortLabel.value = sortLabels[currentSort.value]

      if (currentSort.value !== 'NONE') {
        emit('update:modelValue', currentSort.value)
      } else {
        emit('update:modelValue', undefined)
      }
    }

    const selectedButton = ref('')
    const buttonState = ref({})

    const onButtonClick = (type) => {
      selectedButton.value = type
      emit('button-clicked', type)
    }

    const activeIcon = (type) => {
      return buttonState.value[type] === 'DESC'
        ? 'mdi-arrow-down'
        : 'mdi-arrow-up'
    }

    watch(
      () => props.modelValue,
      (newValue) => {
        console.debug(`filterSortList: modelValue changed to ${newValue}`)
        if (newValue) {
          const [type, state] = newValue.split('_')
          selectedButton.value = type
          buttonState.value[type] = state
        } else {
          selectedButton.value = ''
          buttonState.value = {}
        }
      }
    )

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
