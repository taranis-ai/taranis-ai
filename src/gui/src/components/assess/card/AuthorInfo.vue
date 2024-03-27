<template>
  <tr v-if="author">
    <td style="max-width: 110px" class="py-0">
      <strong>{{ $t('assess.author') }}:</strong>
    </td>
    <td class="py-0">
      {{ author }}
    </td>
  </tr>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'AuthorInfo',
  props: {
    newsItemData: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const author = computed(() => {
      return props.newsItemData?.author
    })

    return {
      author
    }
  }
}
</script>
