<template>
  <iframe :src="iframeSrc" title="OpenAPI" class="frontend-iframe"></iframe>
</template>

<script>
export default {
  name: 'OpenAPI',
  setup() {
    const iframeSrc = `${import.meta.env.BASE_URL}frontend/doc`
    return { iframeSrc }
  }
}
</script>
