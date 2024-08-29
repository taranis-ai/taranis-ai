<template>
  <v-dialog v-model="hotkeyDialogVisible" max-width="600px">
    <HotKeysLegend :show-close-button="true" />
  </v-dialog>
</template>

<script>
import { defineComponent } from 'vue'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'
import HotKeysLegend from '@/views/users/settings/HotKeysLegend.vue'

export default defineComponent({
  name: 'HotKeysDialogView',
  components: {
    HotKeysLegend
  },
  setup() {
    const { hotkeyDialogVisible } = storeToRefs(useMainStore())

    return { hotkeyDialogVisible }
  }
})
</script>

<style scoped>
.notification {
  bottom: 50px !important;
}
</style>
