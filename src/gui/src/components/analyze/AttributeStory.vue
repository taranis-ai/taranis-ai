<template>
  <v-autocomplete
    v-model="input"
    :readonly="readOnly"
    :label="title"
    :items="stories"
    item-text="title"
    item-value="id"
    multiple
    closable-chips
    clearable
    variant="outlined"
    no-data-text="No Stories found"
  />
</template>

<script>
import { computed, inject } from 'vue'

export default {
  name: 'AttributeStory',
  props: {
    modelValue: {
      type: Array,
      default: () => [],
      required: true
    },
    title: {
      type: String,
      default: 'Stories'
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
