<template>
  <v-tooltip open-delay="1000" bottom :disabled="!tooltip">
    <template v-slot:activator="{ on, attrs }">
      <v-btn
        v-bind="attrs"
        v-on="on"
        icon
        tile
        class="news-item-action"
        :class="[{ active: active ? active : false }, extraClass]"
        @click.native.capture="execute($event)"
      >
        <v-icon> {{ icon }} </v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>

<script>
export default {
  name: 'newsItemAction',
  props: {
    active: Boolean,
    icon: String,
    extraClass: String,
    tooltip: String
  },
  methods: {
    execute (event) {
      event.stopPropagation()
      this.$emit('click', event)
    }
  }
}
</script>
