<template>
  <v-combobox
    v-model="tags"
    :items="modelValue"
    chips
    density="compact"
    closable-chips
    clearable
    variant="outlined"
    no-data-text="No tags found"
    hint="Press 'Enter' to add a new tag"
    persistent-hint
    item-value="name"
    item-title="name"
    label="Tags"
    multiple
  />
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'EditTags',
  props: {
    modelValue: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const updatedTags = ref(props.modelValue)

    const updateTags = (val) => {
      updatedTags.value = val
      emit('update:modelValue', val)
    }

    return {
      tags: computed({
        get: () => updatedTags.value,
        set: updateTags
      })
    }
  }
}
</script>
