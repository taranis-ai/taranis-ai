<template>
  <v-container>
    <v-row class="mt-3">
      <v-col cols="2">
        <v-text-field
          v-model="intervalData.weeks"
          type="number"
          label="Weeks"
          variant="outlined"
        />
      </v-col>
      <v-col cols="2">
        <v-text-field
          v-model="intervalData.days"
          type="number"
          label="Days"
          variant="outlined"
        />
      </v-col>
      <v-col cols="2">
        <v-text-field
          v-model="intervalData.hours"
          type="number"
          label="Hours"
          variant="outlined"
        />
      </v-col>
      <v-col cols="2">
        <v-text-field
          v-model="intervalData.minutes"
          type="number"
          label="Minutes"
          variant="outlined"
        />
      </v-col>
      <v-col cols="2">
        <v-text-field
          v-model="intervalData.seconds"
          type="number"
          label="Seconds"
          variant="outlined"
        />
      </v-col>
    </v-row>

    <v-row class="mt-3">
      <v-col cols="5">
        <date-filter
          placeholder="Start Date"
          tooltip-text="Date when the refresh interval starts to be applied"
        />
      </v-col>
      <v-col cols="5">
        <date-filter
          placeholder="End Date"
          tooltip-text="Date when the refresh interval starts to be applied"
        />
      </v-col>
      <v-col cols="2">
        <v-text-field
          v-model="intervalData.jitter"
          type="number"
          label="Jitter (s)"
          variant="outlined"
        />
      </v-col>
    </v-row>

    <v-row class="mt-3">
      <v-col cols="12">
        <cron-vuetify v-model="value" @error="error = $event" />
      </v-col>
    </v-row>

    <v-row class="mt-3">
      <v-col cols="12">
        <v-text-field
          class="pt-3"
          :modelValue="value"
          @update:model-value="nextValue = $event"
          @blur="value = nextValue"
          label="cron expression"
          :error-messages="error"
          variant="outlined"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import dateFilter from '@/components/common/filter/dateFilter.vue'
import { CronVuetify } from '@vue-js-cron/vuetify'
import { defineProps, defineEmits, computed, ref } from 'vue'

const props = defineProps({
  modelValue: Object
})
const emit = defineEmits(['update:modelValue'])

const intervalData = computed({
  get: () => props.modelValue || {},
  set: (value) => emit('update:modelValue', value)
})

const value = ref('* * * * *')
const nextValue = ref('* * * * *')
const error = ref('')
</script>

<style scoped>
@import '@vue-js-cron/vuetify/dist/vuetify.css';
</style>
