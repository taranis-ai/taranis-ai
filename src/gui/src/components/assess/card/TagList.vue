<template>
  <div v-if="tags" class="story-tag-list">
    <v-tooltip
      v-for="(tag, i) in [...new Set(tags.slice(0, limit))]"
      :key="i"
      location="top"
      transition="fade-transition"
    >
      <template #activator="{ props }">
        <v-chip
          v-bind="props"
          class="py-3 mr-1 mt-1"
          :color="labelcolor(tag.tag_type)"
          link
          label
          density="compact"
          :variant="truncate ? 'tonal' : 'elevated'"
          elevation="0"
          size="x-small"
          @click.stop="updateTags(tag.name)"
        >
          <template #prepend>
            <v-icon :icon="tagIcon(tag.tag_type)" size="x-small" class="mr-2" />
          </template>

          <span class="d-inline-block text-truncate tag-content">
            {{ tag.name }}
          </span>
        </v-chip>
      </template>

      <span>
        <v-icon start :icon="tagIcon(tag.tag_type)" size="x-small" />
        {{ tag.name }} - {{ tag.tag_type }}
      </span>
    </v-tooltip>
    <v-tooltip v-if="editable" text="edit tags" location="bottom">
      <template #activator="{ props }">
        <v-chip
          v-bind="props"
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
          <!-- edit -->
          <v-icon icon="mdi-pencil-outline" size="small" />
        </v-chip>
      </template>
    </v-tooltip>
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
    limit: {
      type: Number,
      default: 5
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
  flex-wrap: v-bind(flex_wrap);
}
.tag-content {
  max-width: v-bind(max_width);
}
</style>
