<template>
  <v-snackbar
    v-model="notification.show"
    close-on-content-click
    close-on-back
    rounded
    timer
    min-height="4.5em"
    variant="flat"
    width="80%"
    content-class="bottom-0 mb-16 right-0 mr-4"
    max-width="80%"
    class="d-block"
    :timeout="notification.timeout"
    :text="notificationContent"
    :color="notification.type"
  />
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
