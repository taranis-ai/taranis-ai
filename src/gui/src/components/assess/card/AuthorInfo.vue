<template>
  <v-row v-if="author">
    <v-col style="max-width: 110px" class="py-0">
      <strong>{{ $t('assess.author') }}:</strong>
    </v-col>
    <v-col class="py-0">
      {{ author }}
    </v-col>
  </v-row>
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
