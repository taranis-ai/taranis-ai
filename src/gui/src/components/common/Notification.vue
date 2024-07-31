<template>
  <v-snackbar
    v-model="notification.show"
    dark
    close-on-content-click
    min-height="4.5em"
    :rounded="false"
    variant="flat"
    offset="0"
    width="100%"
    max-width="100%"
    class="notification opacity-90 d-block h-100"
    content-class="bottom-0"
    :timer="notification.timeout > 0"
    :timeout="notification.timeout"
    :text="notificationContent"
    :color="notification.type"
    style="z-index: 100"
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

<style lang="scss">
.notification .v-progress-linear__determinate {
  filter: brightness(0.7) !important;
}
</style>
