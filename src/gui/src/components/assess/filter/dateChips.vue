<template>
  <v-chip-group
    :value="defaultValue"
    @change="setValue"
    active-class="selected"
    class="date-filter-group d-flex"
  >
    <v-chip label outlined dark value="all">all</v-chip>
    <v-chip label outlined dark value="today">today</v-chip>
    <v-chip label outlined dark value="week">one week</v-chip>
  </v-chip-group>
</template>

<script>
export default {
  name: 'dateChips',
  props: {
    label: String,
    value: String
  },
  methods: {
    setValue (newValue) {
      this.$emit('input', newValue)
    }
  },
  computed: {
    defaultValue () {
      return this.value ? this.value : 'all'
    }
  }
}
</script>
