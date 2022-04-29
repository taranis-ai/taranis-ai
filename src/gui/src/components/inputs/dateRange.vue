<template>
  <v-menu
    ref="datePicker"
    v-model="datePickerOpen"
    :return-value.sync="value"
    :close-on-content-click="false"
    transition="scale-transition"
    offset-y
    min-width="auto"
  >
    <!-- formatted display in textfield -->
    <template v-slot:activator="{ on, attrs }">
      <v-text-field
        readonly
        outlined
        dense
        append-icon="mdi-calendar-range-outline"
        v-model="formattedDateRange"
        v-bind="attrs"
        v-on="on"
        placeholder="Date range"
        hide-details
        :class="[{ 'text-field-active': value.range.length }]"
      ></v-text-field>
    </template>

    <!-- datepicker -->
    <v-date-picker
      v-model="value.range"
      range
      no-title
      scrollable
      color="primary"
      @change="value.selected = 'range'"
    >
      <v-spacer></v-spacer>

      <!-- Buttons -->
      <v-btn
        text
        outlined
        class="text-lowercase grey--text text--darken-2"
        @click="clearAndFallback()"
      >
        Cancel
      </v-btn>

      <v-btn
        text
        outlined
        color="primary"
        @click="$refs.datePicker.save(value)"
      >
        OK
      </v-btn>
    </v-date-picker>
  </v-menu>
</template>

<script>
export default {
  name: 'dateRange',
  props: {
    value: {}
  },
  data: () => ({
    datePickerOpen: false
  }),
  methods: {
    clearAndFallback () {
      this.value.range = []
      this.value.selected = 'all'
      this.datePickerOpen = false
    }
  },
  computed: {
    formattedDateRange () {
      return this.value.range.join(' – ')
    }
  }
}
</script>
