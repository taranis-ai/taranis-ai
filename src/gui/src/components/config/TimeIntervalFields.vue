<template>
  <v-container>
    <v-card class="pa-4 mb-4">
      <v-card-title class="text-h6">Refresh Interval</v-card-title>
      <v-divider></v-divider>

      <v-card-text>
        <v-row class="mt-3">
          <v-col cols="12">
            <cron-vuetify v-model="value" @error="error = $event" />
          </v-col>
        </v-row>

        <v-row class="mt-3">
          <v-col cols="3">
            <v-text-field
              class="pt-3 cron-input"
              :modelValue="value"
              @update:model-value="nextValue = $event"
              @blur="value = nextValue"
              label="Cron Expression"
              :error-messages="error"
              variant="outlined"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { CronVuetify } from '@vue-js-cron/vuetify'

const value = ref('* * * * *')
const nextValue = ref('* * * * *')
const error = ref('')
</script>

<style scoped>
@import '@vue-js-cron/vuetify/dist/vuetify.css';

.cron-input {
  width: 100%;
}
</style>
