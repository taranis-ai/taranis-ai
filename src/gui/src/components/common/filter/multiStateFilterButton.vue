<template>
  <v-btn
    class="vertical-button"
    :color="buttonColor"
    :prepend-icon="icon"
    variant="text"
    @click="toggleState()"
  >
    {{ labelText }}
  </v-btn>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'MultiStateFilterButton',
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    label: {
      type: String,
      default: ''
    },
    icon: {
      type: String,
      default: ''
    },
    values: {
      type: Array,
      required: true
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    function toggleState() {
      const currentIndex = props.values.indexOf(props.modelValue)

      if (currentIndex === -1) {
        emit('update:modelValue', props.values[0])
      } else if (currentIndex === props.values.length - 1) {
        emit('update:modelValue', undefined)
      } else {
        emit('update:modelValue', props.values[currentIndex + 1])
      }
    }

    const labelText = computed(() => {
      const currentIndex = props.values.indexOf(props.modelValue)

      if (props.modelValue) {
        return props.label + ' - ' + props.values[currentIndex]
      }
      return props.label
    })

    const buttonColor = computed(() => {
      if (props.modelValue) {
        return 'default'
      }
      return 'dark-grey'
    })

    return {
      toggleState,
      labelText,
      buttonColor
    }
  }
}
</script>
