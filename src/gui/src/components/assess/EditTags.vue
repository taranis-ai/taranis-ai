<template>
  <v-combobox
    v-model="tags"
    :items="tagsArray"
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
      type: Object,
      default: () => ({})
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const tagsArray = computed(() => {
      return Object.values(props.modelValue || {})
    })

    const updatedTags = ref(tagsArray.value)

    const updateTags = (val) => {
      updatedTags.value = val
      
      // Convert Array back to Object format for parent component
      const tagsObject = {}
      if (Array.isArray(val)) {
        val.forEach(tag => {
          if (typeof tag === 'string') {
            // Handle new tags entered as strings
            tagsObject[tag] = { name: tag, tag_type: 'UNKNOWN' }
          } else if (tag && tag.name) {
            // Handle existing tag objects
            tagsObject[tag.name] = tag
          }
        })
      }
      
      emit('update:modelValue', tagsObject)
    }

    return {
      tagsArray,
      tags: computed({
        get: () => updatedTags.value,
        set: updateTags
      })
    }
  }
}
</script>
