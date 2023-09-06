<template>
  <div v-if="tags" class="ml-0 pl-0 d-flex flex-wrap">
    <v-tooltip v-for="(tag, i) in tags.slice(0, limit)" :key="i">
      <template #activator="{ props }">
        <v-chip
          v-bind="props"
          class="mr-1 mt-1"
          :color="labelcolor(tag.tag_type)"
          link
          label
          density="compact"
          :prepend-icon="tagIcon(tag.tag_type)"
          @click.stop="updateTags(tag.name)"
        >
          <span
            :style="truncate ? 'max-width: 80px' : 'max-width: 120px'"
            class="d-inline-block text-truncate text-black"
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
import { useAssessStore } from '@/stores/AssessStore'
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
    }
  },
  setup(props) {
    const { appendTag } = useFilterStore()
    const { updateNewsItems } = useAssessStore()

    const updateTags = (tag) => {
      appendTag(tag)
      updateNewsItems()
    }

    function labelcolor(inputString) {
      if (!props.color) {
        return ''
      }

      const colorList = ['red', 'blue', 'green', 'black']
      const hash = inputString.split('').reduce((acc, char) => {
        return acc + char.charCodeAt(0)
      }, 0)
      const colorIndex = hash % colorList.length
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
