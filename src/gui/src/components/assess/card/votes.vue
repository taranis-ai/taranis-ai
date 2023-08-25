<template>
  <v-btn-toggle>
    <v-btn
      v-ripple="false"
      size="small"
      class="item-action-btn"
      variant="tonal"
      @click.stop="vote('like')"
    >
      <span>{{ story.likes }}</span>
      <v-icon
        right
        color="awake-green-color"
        icon="mdi-arrow-up-circle-outline"
      />
    </v-btn>
    <v-btn
      v-ripple="false"
      size="small"
      class="item-action-btn"
      variant="tonal"
      @click.stop="vote('dislike')"
    >
      <span>{{ story.dislikes }}</span>
      <v-icon
        right
        color="awake-red-color"
        icon="mdi-arrow-down-circle-outline"
      />
    </v-btn>
  </v-btn-toggle>
</template>

<script>
import { useAssessStore } from '@/stores/AssessStore'

export default {
  name: 'StoryVotes',
  props: {
    story: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const assessStore = useAssessStore()

    const vote = (vote) => {
      assessStore.voteOnNewsItemAggregate(props.story.id, vote)
    }

    return {
      vote
    }
  }
}
</script>
