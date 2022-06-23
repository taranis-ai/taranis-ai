<template>
  <div class="align-self-center">
    <v-icon
      v-if="type === 'up'"
      left
      small
      color="awake-green-color"
      class="mr-1"
      @click.native.capture="setValue($event)"
      >mdi-arrow-up-circle-outline</v-icon
    >
    <v-icon
      v-if="type === 'down'"
      left
      small
      color="awake-red-color"
      class="mr-1"
      @click.native.capture="setValue($event)"
      >mdi-arrow-down-circle-outline</v-icon
    >
    <span
      class="
        text-caption
        font-weight-light
        dark-grey--text
      "
      >{{ count }}</span
    >
  </div>
</template>

<script>
export default {
  name: 'votes',
  props: {
    count: Number,
    type: String
  },
  methods: {
    setValue (event) {
      this.$emit('input', event)
      event.stopPropagation()
    }
  }
}
</script>
