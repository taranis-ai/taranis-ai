<template>
    <v-chip
      label
      class="mr-1 mb-1 topic-label"
      dark
      x-small
      :color="labelcolor(tag.color)"
      >
        {{ tag.label }}
    </v-chip>
</template>

<script>
export default {
  name: 'TagNorm',
  props: {
    tag: {}
  },
  data: () => ({
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
      return colorList[i % colorList.length]
    }
  }
}
</script>
