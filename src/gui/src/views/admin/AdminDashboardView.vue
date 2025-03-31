<template>
  <iframe :src="iframeSrc" class="frontend-iframe" />
</template>

<script>
export default {
  name: 'AdminDashboard',
  setup() {
    const iframeSrc = `${import.meta.env.BASE_URL}frontend`

    return { iframeSrc }
  }
}
</script>
