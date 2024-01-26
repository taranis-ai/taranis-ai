<template>
  <v-btn
    class="vertical-button"
    :color="buttonColor"
    :prepend-icon="icon"
    :append-icon="activeIcon"
    variant="text"
    @click="toggleState()"
  >
    {{ labelText }}
  </v-btn>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'FilterButton',
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
    enabledValue: {
      type: String,
      default: 'true'
    },
    disabledValue: {
      type: String,
      default: 'false'
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    function toggleState() {
      if (props.modelValue === props.enabledValue) {
        emit('update:modelValue', props.disabledValue)
      } else if (props.modelValue === props.disabledValue) {
        emit('update:modelValue', undefined)
      } else {
        emit('update:modelValue', props.enabledValue)
      }
    }

    const labelText = computed(() => {
      if (props.modelValue === props.enabledValue) {
        return props.label
      }
      if (props.modelValue === props.disabledValue) {
        return 'not ' + props.label
      }
      return props.label
    })

    const buttonColor = computed(() => {
      if (props.modelValue === props.enabledValue) {
        return 'primary'
      }
      if (props.modelValue === props.disabledValue) {
        return 'default'
      }
      return 'dark-grey'
    })

    const activeIcon = computed(() => {
      if (props.modelValue === props.enabledValue) {
        return 'mdi-check-bold'
      }
      if (props.modelValue === props.disabledValue) {
        return 'mdi-close'
      }
      return ''
    })

    return {
      toggleState,
      labelText,
      buttonColor,
      activeIcon
    }
  }
}
</script>
