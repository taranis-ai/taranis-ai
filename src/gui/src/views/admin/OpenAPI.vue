<template>
  <iframe :src="iframeSrc" title="OpenAPI" class="openapi"></iframe>
</template>

<script>
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'OpenAPI',
  setup() {
    const store = useMainStore()
    const iframeSrc = store.coreAPIURL + '/doc'
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
