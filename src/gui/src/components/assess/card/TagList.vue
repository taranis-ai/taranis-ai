<template>
  <div v-if="tags" class="story-tag-list">
    <v-chip
      v-for="(tag, i) in tags"
      :key="i"
      class="py-3 mr-1 mt-1"
      :color="labelcolor(tag.tag_type)"
      link
      label
      density="compact"
      :variant="truncate ? 'tonal' : 'elevated'"
      elevation="0"
      size="x-small"
      :prepend-icon="tagIcon(tag.tag_type)"
      @click.stop="updateTags(tag.name)"
    >
      <span class="d-inline-block text-truncate tag-content">
        {{ tag.name }}
      </span>
      <v-tooltip
        activator="parent"
        :text="`${tag.name} - ${tag.tag_type}`"
        location="top"
      />
    </v-chip>
    <v-chip
      v-if="editable"
      class="py-3 mr-1 mt-1"
      color="primary"
      link
      label
      density="compact"
      variant="tonal"
      elevation="0"
      size="small"
      icon="mdi-tag-hidden"
      @click.prevent="$emit('edit')"
    >
      <v-icon icon="mdi-pencil-outline" size="small" />
      <v-tooltip activator="parent" text="edit tags" location="top" />
    </v-chip>
  </div>
</template>

<script>
import { defineComponent, computed } from 'vue'
import { tagIconFromType } from '@/utils/helpers'
import { useFilterStore } from '@/stores/FilterStore'
import { useRoute, useRouter } from 'vue-router'

export default defineComponent({
  name: 'TagList',
  props: {
    tags: {
      type: Array,
      required: true
    },
    truncate: {
      type: Boolean,
      default: true
    },
    editable: {
      type: Boolean,
      default: false
    },
    color: {
      type: Boolean,
      default: true
    },
    wrap: {
      type: Boolean,
      default: false
    }
  },
  emits: ['edit'],
  setup(props) {
    const { appendTag } = useFilterStore()
    const route = useRoute()
    const router = useRouter()

    const max_width = computed(() => (props.truncate ? '60px' : '120px'))

    const flex_wrap = computed(() => (props.wrap ? 'wrap' : 'nowrap'))

    const updateTags = (tag) => {
      if (route.name !== 'assess') {
        router.push({ name: 'assess', query: { tags: tag } })
      } else {
        appendTag(tag)
      }
    }

    function labelcolor(inputString) {
      if (!props.color) {
        return ''
      }

      const colorList = [
        '#ddbc42',
        '#d3802b',
        '#d35a2b',
        '#bb432b',
        '#ac004b',
        '#a0062f',
        '#8F1616',
        '#b0309a',
        '#9752cb',
        '#7468e8'
      ]
      const hash = inputString.split('').reduce((acc, char) => {
        return acc + char.charCodeAt(0)
      }, 0)

      const colorIndex = parseInt(hash) % colorList.length
      return colorList[colorIndex]
    }

    const tagIcon = (tag_type) => {
      return tagIconFromType(tag_type)
    }

    return {
      max_width,
      flex_wrap,
      updateTags,
      labelcolor,
      tagIcon
    }
  }
})
</script>

<style scoped>
.story-tag-list {
  display: flex;
  flex-wrap: wrap;
}
.tag-content {
  max-width: v-bind(max_width);
}
</style>
