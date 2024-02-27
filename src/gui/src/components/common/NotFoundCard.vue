<template>
  <v-container fluid>
    <v-card
      class="justify-center d-flex"
      :title="card_title"
      :subtitle="card_subtitle"
    />
  </v-container>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'NotFoundCard',
  props: {
    itemId: {
      type: String,
      required: true
    },
    itemType: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const card_title = computed(() => {
      return `${props.itemType} not Found`
    })
    const card_subtitle = computed(() => {
      return `${props.itemType} with ID: '${props.itemId}' not found.`
    })
    return {
      card_title,
      card_subtitle
    }
  }
}
</script>
