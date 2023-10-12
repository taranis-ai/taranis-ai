<template>
  <v-snackbar v-model="notification.show" dark :color="notification.type">
    <v-row class="fill-height" no-gutters>
      <v-col class="d-flex align-center">
        <span class="text-subtitle-1">{{ notificationContent }}</span>
      </v-col>
      <v-col class="d-flex justify-end align-center">
        <v-btn
          color="black"
          icon="mdi-close"
          size="small"
          @click="notification.show = false"
        />
      </v-col>
    </v-row>
  </v-snackbar>
</template>

<script>
import { defineComponent } from 'vue'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

export default defineComponent({
  name: 'NotificationView',

  setup() {
    const { t, te } = useI18n()

    const { notification } = storeToRefs(useMainStore())
    const notificationContent = computed(() => {
      if (
        !('message' in notification.value) ||
        typeof notification.value.message != 'string'
      )
        return ''
      return te(notification.value.message)
        ? t(notification.value.message)
        : notification.value.message
    })

    return { notification, notificationContent }
  }
})
</script>
