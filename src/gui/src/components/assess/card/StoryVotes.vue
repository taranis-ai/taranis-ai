<template>
  <v-btn-toggle>
    <v-btn
      v-ripple="false"
      size="small"
      class="vote-btn left-vote-btn"
      variant="outlined"
      density="compact"
      @click.stop="vote('like')"
    >
      <span>{{ likes }}</span>
      <v-icon
        right
        size="small"
        class="ml-1"
        color="awake-green-color"
        icon="mdi-arrow-up-circle-outline"
      />
    </v-btn>
    <v-btn
      v-ripple="false"
      size="small"
      class="vote-btn right-vote-btn"
      variant="outlined"
      density="compact"
      @click.stop="vote('dislike')"
    >
      <span>{{ dislikes }}</span>
      <v-icon
        right
        size="small"
        class="ml-1"
        color="awake-red-color"
        icon="mdi-arrow-down-circle-outline"
      />
    </v-btn>
  </v-btn-toggle>
</template>

<script>
import { ref } from 'vue'
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

    const likes = ref(props.story.likes)
    const dislikes = ref(props.story.dislikes)
    const relevance = ref(props.story.relevance)
    const voted = ref(props.story.user_vote)

    const vote = (vote) => {
      assessStore.voteOnNewsItemAggregate(props.story.id, vote)
      updateVote(vote)
    }

    function updateVote(vote) {
      if (vote === 'like') {
        if (voted.value.like) {
          likes.value -= 1
          relevance.value -= 1
          voted.value.like = false
        } else if (voted.value.dislike) {
          dislikes.value -= 1
          likes.value += 1
          relevance.value += 2
          voted.value = { like: true, dislike: false }
        } else {
          likes.value += 1
          relevance.value += 1
          voted.value.like = true
        }
      }
      if (vote === 'dislike') {
        if (voted.value.dislike) {
          dislikes.value -= 1
          relevance.value += 1
          voted.value.dislike = false
        } else if (voted.value.like) {
          likes.value -= 1
          dislikes.value += 1
          relevance.value -= 2
          voted.value = { like: false, dislike: true }
        } else {
          dislikes.value += 1
          relevance.value -= 1
          voted.value.dislike = true
        }
      }
    }

    return {
      vote,
      likes,
      dislikes
    }
  }
}
</script>

<style lang="scss">
.vote-btn {
  flex: 1;
  height: 28px !important;
  min-width: fit-content;
}
.left-vote-btn {
  border-right: 1px solid #e0e0e0 !important;
}
</style>
