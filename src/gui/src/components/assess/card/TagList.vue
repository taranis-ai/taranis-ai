<template>
  <div v-if="tags" class="ml-0 pl-0 d-flex" :class="{ 'flex-wrap': wrap }">
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
          @click.stop="updateTags(tag.name)"
        >
          <template #prepend>
            <v-icon
              :icon="tagIcon(tag.tag_type)"
              size="x-small"
              class="mr-2"
              :class="{ truncate: 'text-white' }"
            >
            </v-icon>
          </template>

          <span
            :style="truncate ? 'max-width: 80px' : 'max-width: 120px'"
            class="d-inline-block text-truncate"
            :class="{ truncate: 'text-white' }"
          >
            {{ tag.name }}
          </span>
        </v-chip>
      </template>

      <span>
        <v-icon start :icon="tagIcon(tag.tag_type)" />
        {{ tag.name }} - {{ tag.tag_type }}
      </span>
    </v-tooltip>
  </div>
</template>

<script>
import { defineComponent } from 'vue'
import { tagIconFromType } from '@/utils/helpers'
import { useFilterStore } from '@/stores/FilterStore'

export default defineComponent({
  name: 'TagList',
  props: {
    tags: {
      type: Array,
      required: true
    },
    limit: {
      type: Number,
      default: 6
    },
    truncate: {
      type: Boolean,
      default: true
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
  setup(props) {
    const { appendTag } = useFilterStore()

    const updateTags = (tag) => {
      appendTag(tag)
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
      updateTags,
      labelcolor,
      tagIcon
    }
  }
})
</script>
