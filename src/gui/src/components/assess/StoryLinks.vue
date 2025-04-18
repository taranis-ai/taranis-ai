<template>
  <div class="d-flex">
    <v-combobox
      v-model="links"
      :items="modelValue"
      chips
      density="compact"
      closable-chips
      clearable
      variant="outlined"
      no-data-text="No links sets"
      hint="Press 'Enter' to add a new link"
      persistent-hint
      item-value="news_item_id"
      item-title="link"
      label="Links"
      multiple
    />
    <v-btn class="ml-3" color="primary" @click="updateLinksFromNewsItems">
      {{ $t('enter.updatelinks') }}
    </v-btn>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { v4 as uuidv4 } from 'uuid'

export default {
  name: 'StoryLinks',
  props: {
    modelValue: {
      type: Array,
      default: () => []
    },
    newsItems: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const currentLinks = ref([...props.modelValue])

    function updateLinks(val) {
      const transformedLinks = val.map((item) => {
        if (typeof item === 'string') {
          return {
            news_item_id: `manual_${uuidv4()}`,
            link: item
          }
        }
        return item
      })

      currentLinks.value = transformedLinks
      emit('update:modelValue', transformedLinks)
    }

    function updateLinksFromNewsItems() {
      const manualEntries = currentLinks.value.filter((link) =>
        link.news_item_id.startsWith('manual_')
      )

      const newsItemLinks = props.newsItems.map((item) => {
        return {
          news_item_id: item.id,
          link: item.link
        }
      })

      const updatedLinks = [...manualEntries, ...newsItemLinks]

      updateLinks(updatedLinks)
    }

    return {
      links: computed({
        get: () => currentLinks.value,
        set: updateLinks
      }),
      updateLinksFromNewsItems
    }
  }
}
</script>
