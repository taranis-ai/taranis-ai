<template>
  <tr v-if="author">
    <td v-if="!compactView" style="max-width: 110px" class="py-0">
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
    },
    compactView: {
      type: Boolean,
      default: false
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
