<template>
  <div>
    <v-snackbar dark v-model="notification" :color="notify.type">
      <span>{{ $t(notify.loc) }}</span>
      <v-btn text color="white--text" @click="notification = false">{{
        $t('notification.close')
      }}</v-btn>
    </v-snackbar>
  </div>
</template>

<script>
export default {
  name: 'Notification',

  props: {},
  data: () => ({
    notification: false,
    notify: Object
  }),

  mounted() {
    this.$root.$on('notification', (message) => {
      console.log(message)
      this.notification = true
      this.notify = message
    })
  }
}
</script>
