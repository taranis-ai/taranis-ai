<template>
  <v-autocomplete
    v-model="selected"
    v-model:search="searchState"
    :loading="loading"
    :items="available_tags"
    chips
    density="compact"
    closable-chips
    clearable
    variant="outlined"
    no-data-text="No tags found"
    item-value="name"
    item-title="name"
    label="Tags"
    menu-icon="mdi-chevron-down"
    multiple
  >
    <template #item="{ props, item }">
      <v-list-item
        v-bind="props"
        :prepend-icon="tagIcon(item.raw.tag_type)"
        :text="shortText(item.raw.name)"
      />
    </template>
    <template #chip="{ props, item }">
      <v-chip
        :prepend-icon="tagIcon(item.raw.tag_type)"
        v-bind="props"
        :text="shortText(item.raw.name)"
      />
    </template>
  </v-autocomplete>
</template>

<script>
import { ref, onBeforeMount, computed } from 'vue'
import { getTags } from '@/api/assess'
import { tagIconFromType } from '@/utils/helpers'

export default {
  name: 'TagFilter',
  props: {
    modelValue: {
      type: Array,
      default: () => [],
      required: true
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const selected = computed({
      get: () => {
        return props.modelValue
      },
      set: (val) => {
        emit('update:modelValue', val)
      }
    })
    const available_tags = ref([])
    const search = ref('')
    const loading = ref(false)
    const timeout = ref(null)

    const searchState = computed({
      get: () => search.value,
      set: (value) => {
        search.value = value
        clearTimeout(timeout.value)
        timeout.value = setTimeout(() => {
          value && querySelections({ search: value })
        }, 500)
      }
    })

    const shortText = (item) => {
      return item?.length > 15 ? item.substring(0, 15) + '...' : item
    }

    const tagIcon = (tag_type) => {
      return tagIconFromType(tag_type)
    }

    async function querySelections(filter) {
      loading.value = true
      try {
        const res = await getTags(filter)
        available_tags.value = res.data
        if (typeof selected.value === 'string') {
          if (!available_tags.value.includes(selected.value)) {
            available_tags.value.unshift(selected.value)
          }
        }
        // Check if selected.value is an array
        else if (Array.isArray(selected.value)) {
          selected.value.forEach((tag) => {
            if (!available_tags.value.includes(tag)) {
              available_tags.value.unshift(tag)
            }
          })
        }
        loading.value = false
      } catch (error) {
        console.error(error)
        loading.value = false
      }
    }

    onBeforeMount(async () => {
      querySelections({ search: search.value })
    })

    return {
      selected,
      available_tags,
      searchState,
      loading,
      shortText,
      tagIcon
    }
  }
}
</script>
