<template>
  <v-btn
    fab
    depressed
    outlined
    x-small
    color="grey"
    :class="['fab-pin', { pinned: value }]"
    @click.native.capture="toggleValue($event)"
  >
    <v-icon>mdi-pin</v-icon>
  </v-btn>
</template>

<script>
export default {
  name: 'pin',
  props: {
    value: Boolean
  },
  methods: {
    toggleValue (event) {
      this.$emit('click', !this.value)
      event.stopPropagation()
    }
  }
}
</script>
