<template>
  <v-btn
    outlined
    dark
    @click="$emit('input', !value)"
    :class="['text-lowercase', 'px-0', { selected: value }]"
  >
    <span v-if="value"> & </span>
    <span v-else> or </span>
  </v-btn>
</template>

<script>
export default {
  name: 'logicalAnd',
  props: {
    value: Boolean
  }
}
</script>
