<template>
  <div v-if="tags" class="ml-0 pl-0 d-flex flex-wrap">
    <v-tooltip v-for="(tag, i) in tags.slice(0, limit)" :key="i">
      <template #activator="{ props }">
        <v-chip
          v-bind="props"
          class="mr-1 mt-1"
          :color="labelcolor(i)"
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
        {{ tag.name }}
      </span>
    </v-tooltip>
  </div>
</template>

<script>
import { mapActions } from 'pinia'

import { tagIconFromType } from '@/utils/helpers'
import { useAssessStore } from '@/stores/AssessStore'
import { useFilterStore } from '@/stores/FilterStore'

export default {
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
  data: () => ({
    colorStart: Math.floor(Math.random() * 9)
  }),
  methods: {
    ...mapActions(useAssessStore, ['updateNewsItems']),
    ...mapActions(useFilterStore, ['appendTag']),

    updateTags(tag) {
      this.appendTag(tag)
      this.updateNewsItems()
    },
    tagIcon(tag_type) {
      return tagIconFromType(tag_type)
    },

    labelcolor: function (i) {
      if (!this.color) {
        return ''
      }

      const colorList = ['red', 'blue', 'green', 'black']
      return colorList[(this.colorStart + i) % colorList.length]
    }
  }
}
</script>
