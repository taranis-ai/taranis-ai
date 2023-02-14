<template>
  <div>
      <v-chip
        v-for="(tag, i) in tags.slice(0, limit)"
        :key="i"
        label
        :class="getChipClass"
        dark
        x-small
        :color="labelcolor(i)"
        >
        <span :class="getTagClass">
          {{ tag }}
        </span>
      </v-chip>
  </div>
</template>

<script>
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
    labelcolor: function (i) {
      var colorList = [
        '#DCE868',
        '#DDBC42',
        '#D3802B',
        '#BB432B',
        '#AC004B',
        '#A0062F',
        '#8F1616',
        '#B0309A',
        '#9752CB'
      ]
      return colorList[(this.colorStart + i) % colorList.length]
    }
  }
}
</script>
