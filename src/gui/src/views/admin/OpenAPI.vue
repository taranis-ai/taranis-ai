<template>
  <iframe :src="iframeSrc" title="OpenAPI" class="openapi"></iframe>
</template>

<script>
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'OpenAPI',
  setup() {
    const store = useMainStore()
    store.resetItemCount()
    const iframeSrc = `${import.meta.env.BASE_URL}frontend/doc`
    return { iframeSrc }
  }
}
</script>

<style scoped>
.openapi {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
