<template>
  <v-card-title>
    <span>
      <v-icon :icon="tagIcon" />
      <router-link :to="`/cluster/${tagType}`">
        {{ tagText }}
      </router-link>
    </span>
    <span class="ml-5"> Cluster size: {{ cluster.size }}</span>
    <v-divider class="mt-2 mb-2" />
  </v-card-title>
  <v-card-text>
    <div v-for="item in cluster.tags" :key="item.id">
      <router-link :to="'/assess?tags=' + item.name">
        {{ item.name }}
      </router-link>
      <v-icon class="mr-2"> mdi-chevron-right </v-icon>
      <span class="ml-5"> {{ item.size }} </span>
    </div>
  </v-card-text>
</template>

<script>
import { ref, computed } from 'vue'
import { tagIconFromType, tagTextFromType } from '@/utils/helpers'

export default {
  name: 'TrendingCard',
  props: {
    cluster: { type: Object, required: true }
  },
  setup(props) {
    const tagType = ref(props.cluster.name)

    const tagIcon = computed(() => {
      return tagIconFromType(tagType.value)
    })

    const tagText = computed(() => {
      return tagTextFromType(tagType.value)
    })

    return {
      tagType,
      tagIcon,
      tagText
    }
  }
}
</script>
