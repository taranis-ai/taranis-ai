<template>
  <v-col xs="12" sm="6" md="4" :xl="promValue">
    <card-story :story="story"></card-story>
  </v-col>
</template>

<script>
import CardStory from '@/components/common/card/CardStory'

export default {
  name: 'AdaptiveCardsize',
  components: {
    CardStory
  },
  props: {
    position: Number,
    story: {}
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
