<template>
  <v-btn-toggle>
    <v-btn
      v-ripple="false"
      size="small"
      class="item-action-btn"
      variant="tonal"
      :disabled="voted"
      @click.stop="upvote()"
    >
      <span>{{ likes }}</span>
      <v-icon right color="awake-green-color"
        >mdi-arrow-up-circle-outline</v-icon
      >
    </v-btn>
    <v-btn
      v-ripple="false"
      size="small"
      class="item-action-btn"
      variant="tonal"
      :disabled="voted"
      @click.stop="downvote()"
    >
      <span>{{ dislikes }}</span>
      <v-icon right color="awake-red-color"
        >mdi-arrow-down-circle-outline</v-icon
      >
    </v-btn>
  </v-btn-toggle>
</template>

<script>
import { ref } from 'vue'
import { voteNewsItemAggregate } from '@/api/assess'

export default {
  name: 'StoryVotes',
  props: {
    story: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const likes = ref(props.story.likes)
    const dislikes = ref(props.story.dislikes)
    const voted = ref(props.story.user_has_voted)

    const upvote = () => {
      likes.value += 1
      voted.value = true
      voteNewsItemAggregate(props.story.id, 'like')
    }

    const downvote = () => {
      dislikes.value += 1
      voted.value = true
      voteNewsItemAggregate(props.story.id, 'dislike')
    }

    return {
      likes,
      dislikes,
      voted,
      upvote,
      downvote
    }
  }
}
</script>
