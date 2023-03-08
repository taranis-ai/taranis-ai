<template>
  <div>
  <v-tooltip bottom v-for="(tag, i) in tags.slice(0, limit)" :key="i">
    <template v-slot:activator="{ on, attrs }">
      <v-btn
        small
        text
        density="compact"
        height="auto"
        class="tag-button"
        :color="labelcolor(i)"
        @click.stop="updateTags(tag.name)"
        v-ripple="false"
        v-bind="attrs"
        v-on="on"
      >
        <span class="text-decoration-underline">
          {{ tag.name }}
        </span>
      </v-btn>
    </template>
    <span>
      <v-icon left>{{ tagIcon(tag.tag_type) }}</v-icon>
      {{ tag.tag_type }}
    </span>
  </v-tooltip>
  </div>
</template>

<script>
import { mapActions } from 'vuex'
import { tagIconFromType } from '@/utils/helpers'

export default {
  name: 'TagList',
  props: {
    tags: [],
    limit: {
      type: Number,
      default: 5
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
  computed: {
    getChipClass() {
      const c = 'mr-1 mb-1 story-label'
      return this.truncate ? c : c + '-no-trunc'
    },
    getTagClass() {
      return this.truncate ? 'text-truncate' : ''
    }
  },
  data: () => ({
    colorStart: Math.floor(Math.random() * 9)
  }),
  methods: {
    ...mapActions('assess', ['updateNewsItems']),
    ...mapActions('filter', ['appendTag']),

    updateTags(tag) {
      this.appendTag(tag)
      this.updateNewsItems()
    },
    tagIcon(tag_type) { return tagIconFromType(tag_type) },

    labelcolor: function (i) {
      if (!this.color) {
        return undefined
      }

      var colorList = [
        '#2E3D7C',
        '#282528',
        '#BA292E',
        '#E15D3A'
      ]
      return colorList[(this.colorStart + i) % colorList.length]
    }
  }
}
</script>
