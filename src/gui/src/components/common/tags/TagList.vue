<template>
  <div>
      <v-chip
        v-for="(tag, i) in tags.slice(0, limit)"
        :key="i"
        label
        class="mr-1 mb-1 topic-label"
        dark
        x-small
        :color="labelcolor(i)"
        >
        <span class="text-truncate text-capitalize">
          {{ tag }}
        </span>
      </v-chip>
  </div>
</template>

<script>
export default {
  name: 'TagList',
  props: {
    tags: []
  },
  data: () => ({
    limit: 5,
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
