<template>
  {{ stories }}
</template>

<script>
import { computed, inject } from 'vue'

export default {
  name: 'AttributeTLP',
  props: {
    modelValue: {
      type: String,
      default: '',
      required: true
    },
    title: {
      type: String,
      default: 'TLP'
    },
    readOnly: { type: Boolean, default: false }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const stories = inject('report_stories')
    const input = computed({
      get: () => props.modelValue,
      set: (newValue) => emit('update:modelValue', newValue || '')
    })

    return {
      input,
      stories
    }
  }
}
</script>
