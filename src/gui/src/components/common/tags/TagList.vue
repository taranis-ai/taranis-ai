<template>
  <div>
      <v-chip 
        v-for="tag in tags" :key="tag"
        label
        class="mr-1 mb-1 topic-label"
        dark
        :color="labelcolor(tag.color)"
        >
          {{ tag.label }}
      </v-chip>
  </div>
</template>

<script>
export default {
  name: 'TagList',
  props: {
    tags: {}
  },
  data: () => ({
  }),
  methods: {
    labelcolor: function(i) {
      var colorList = [
        '#DCE868',
        '#DDBC42',
        '#D3802B',
        '#BB432B',
        '#AC004B',
        '#A0062F',
        '#8F1616',
        '#B0309A',
        '#9752CB',
      ];
      return colorList[i % colorList.length]
    }
  }
}
</script>
