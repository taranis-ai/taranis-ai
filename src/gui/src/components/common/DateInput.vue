<template>
  <v-menu
    v-model="menu"
    :close-on-content-click="false"
    :nudge-right="40"
    transition="scale-transition"
    offset-y
    width="290px"
  >
    <template #activator="{ props }">
      <v-text-field
        v-model="date.value"
        :label="caption"
        prepend-icon="event"
        readonly
        v-bind="props"
      >
        style="width: 290px;" ></v-text-field
      >
      <!-- TODO: i18 > :label="caption" -->
    </template>
    <v-date-picker
      v-model="date.value"
      style=""
      @input="menu = false"
    ></v-date-picker>
  </v-menu>
</template>

<script>
export default {
  name: 'DateInput',
  props: {
    caption: {
      type: String,
      default: ''
    }
  },
  data: () => ({
    menu: false,
    date: {}
  })
}
</script>
