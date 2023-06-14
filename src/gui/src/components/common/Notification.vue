<template>
  <v-snackbar v-model="notification.show" dark :color="notification.type">
    <span>{{ notificationContent }}</span>
    <v-btn
      variant="text"
      color="white--text"
      @click="notification.show = false"
    >
      {{ $t('notification.close') }}
    </v-btn>
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
