<template>
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
  <v-btn class="mt-5" color="primary" @click="updateLinksFromNewsItems">
    {{ $t('enter.updatelinks') }}
  </v-btn>
</template>

<script>
import { ref, computed } from 'vue'

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
    const currentLinks = ref(props.modelValue)

    function updateLinks(val) {
      currentLinks.value = val
      emit('update:modelValue', val)
    }

    function updateLinksFromNewsItems() {
      const links = props.newsItems.map((item) => {
        return {
          news_item_id: item.id,
          link: item.link
        }
      })
      updateLinks(links)
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
