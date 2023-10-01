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

    return {
      selectedButton,
      onButtonClick,
      activeIcon
    }
  }
}
</script>
