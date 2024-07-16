<template>
  <tr v-if="author">
    <td v-if="!compactView" style="max-width: 90px" class="py-0">
      <strong>{{ $t('assess.author') }}:</strong>
    </td>
    <td class="py-0">
      {{ author }}
    </td>
  </tr>
</template>

<script>
import { computed } from 'vue'
import { useFilterStore } from '@/stores/FilterStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'AuthorInfo',
  props: {
    newsItem: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const author = computed(() => {
      return props.newsItem?.author
    })

    const filterStore = useFilterStore()
    const { compactView } = storeToRefs(filterStore)

    return {
      author,
      compactView
    }
  }
}
</script>
