<template>
  <v-container fluid class="pa-0 ma-0">
    <v-row>
      <v-col cols="12">
        <v-switch
          v-model="isEnabled"
          label="Define a custom REFRESH_INTERVAL"
        />
      </v-col>
    </v-row>
    <v-card class="pa-4 mb-4">
      <v-card-title class="text-h6">Refresh Interval</v-card-title>
      <v-divider></v-divider>
      <v-card-text>
        <v-row class="mt-3">
          <v-col cols="12">
            <CronVuetify
              :key="cronIntervalKey"
              v-model="cronInterval"
              @error="error = $event"
              :disabled="!isEnabled"
            />
          </v-col>
        </v-row>
        <v-row class="mt-3">
          <v-col cols="3">
            <v-text-field
              class="pt-3 cron-input"
              v-model="cronInterval"
              label="Cron Expression"
              :error-messages="error"
              variant="outlined"
              :disabled="!isEnabled"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { CronVuetify } from '@vue-js-cron/vuetify'
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const error = ref('')

const cronInterval = computed({
  get() {
    return props.modelValue
  },
  set(newValue) {
    emit('update:modelValue', newValue)
  }
})

const cronIntervalKey = computed(() => cronInterval.value)

const isEnabled = computed({
  get() {
    return cronInterval.value !== ''
  },
  set(value) {
    if (value) {
      emit('update:modelValue', '* */8 * * *')
    } else {
      emit('update:modelValue', '')
    }
  }
})
</script>

<style scoped>
@import '@vue-js-cron/vuetify/dist/vuetify.css';
.cron-input {
  width: 100%;
}
</style>
