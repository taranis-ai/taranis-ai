<template>
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
</template>

<script setup>
import { defineProps, defineEmits, computed } from 'vue'
import dateFilter from '@/components/common/filter/dateFilter.vue'

const props = defineProps({
  modelValue: Object
})

const emit = defineEmits(['update:modelValue'])

const intervalData = computed({
  get: () => props.modelValue || {},
  set: (value) => emit('update:modelValue', value)
})
</script>
