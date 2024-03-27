<template>
  <v-snackbar
    v-model="notification.show"
    dark
    close-on-content-click
    min-height="4.5em"
    class="notification"
    :color="notification.type"
    :timer="true"
    :timeout="20000"
    :text="notificationContent"
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

<style scoped>
.notification {
  bottom: 50px !important;
}
</style>
