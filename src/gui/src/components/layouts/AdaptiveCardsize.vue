<template>
  <v-col xs="12" sm="6" md="4" :xl="promValue">
    <card-topic :topic="topic"></card-topic>
  </v-col>
</template>

<script>
import CardTopic from '@/components/common/card/CardTopic'

export default {
  name: 'AdaptiveCardsize',
  components: {
    CardTopic
  },
  props: {
    position: Number,
    topic: {}
  },
  computed: {
    promValue () {
      if (this.$vuetify.breakpoint.xl) {
        return this.position < 4 ? 3 : 2
      } else {
        return this.position < 3 ? 4 : 3
      }
    }
  }
}
</script>
