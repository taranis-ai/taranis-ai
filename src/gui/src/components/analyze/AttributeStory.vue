<template>
  <v-autocomplete
    v-model="selected"
    :readonly="readOnly"
    :label="title"
    :items="stories"
    :multiple="multiple"
    closable-chips
    clearable
    variant="outlined"
    no-data-text="No Stories found"
  />
</template>

<script>
import { computed, inject, ref } from 'vue'

export default {
  name: 'AttributeStory',
  props: {
    modelValue: {
      type: String,
      required: true
    },
    title: {
      type: String,
      default: 'Stories'
    },
    readOnly: { type: Boolean, default: false },
    multiple: { type: Boolean, default: true }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const stories = inject('report_stories')
    const selected = ref(
      props.modelValue
        .split(',')
        .filter((v) => v)
        .map((val) => val)
    )

    const updateSelected = (val) => {
      selected.value = val
      console.debug('updateSelected', val)
      emit('update:modelValue', val.filter((v) => v).join(','))
    }

    return {
      selected: computed({
        get: () => selected.value,
        set: updateSelected
      }),
      stories
    }
  }
}
</script>
