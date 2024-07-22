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
      <span>{{ story.likes }}</span>
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
      <span>{{ story.dislikes }}</span>
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

    function vote(vote) {
      assessStore.voteOnStory(props.story.id, vote)
    }

    return {
      vote
    }
  }
}
</script>

<style lang="scss" scoped>
.vote-btn {
  flex: 1;
  height: 28px !important;
  min-width: fit-content;
}
.left-vote-btn {
  border-right: 1px solid #e0e0e0 !important;
}
</style>
