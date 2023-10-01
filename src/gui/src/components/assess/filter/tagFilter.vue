<template>
  <div>
    <v-autocomplete
      v-model="selected"
      v-model:search="search"
      :loading="loading"
      :items="available_tags"
      chips
      density="compact"
      deletable-chips
      clearable
      clear-icon="mdi-close"
      variant="outlined"
      no-data-text="No tags found"
      item-value="name"
      item-title="name"
      label="Tags"
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
  </div>
</template>

<script>
import { ref, watch, onMounted, computed } from 'vue'
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

    const shortText = (item) => {
      return item?.length > 15 ? item.substring(0, 15) + '...' : item
    }

    const tagIcon = (tag_type) => {
      return tagIconFromType(tag_type)
    }

    const querySelections = async (filter) => {
      loading.value = true
      await getTags(filter).then((res) => {
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
      })
    }

    watch(search, (val) => {
      val && querySelections({ search: val })
    })

    onMounted(() => {
      querySelections({ search: search.value })
    })

    return {
      selected,
      available_tags,
      search,
      loading,
      shortText,
      tagIcon
    }
  }
}
</script>
