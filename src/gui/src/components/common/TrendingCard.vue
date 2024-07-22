<template>
  <v-card-title class="d-flex justify-space-between">
    <span>
      <v-icon :icon="tagIcon" color="primary" class="mr-3" size="small" />
      <router-link :to="`/cluster/${tagType}`">
        {{ tagText }}
      </router-link>
    </span>
    <span class="ml-5"> Cluster size: {{ cluster.size }}</span>
  </v-card-title>
  <v-divider class="mt-2 mb-2" />
  <v-card-text>
    <v-list density="compact">
      <div v-for="item in cluster.tags" :key="item.id">
        <v-list-item
          :to="'/assess?tags=' + item.name"
          :title="item.name"
          class="tag-item text-black"
        >
          <template #append>
            <span> {{ item.size }} </span>
          </template>
        </v-list-item>
        <v-divider />
      </div>
    </v-list>
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

<style scoped>
.tag-item:hover {
  text-decoration: underline;
}
</style>
