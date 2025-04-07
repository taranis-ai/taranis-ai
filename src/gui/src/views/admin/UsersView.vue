<template>
  <iframe :src="iframeSrc" title="Users" class="frontend-iframe"></iframe>
</template>

<script>
export default {
  name: 'UsersView',
  setup() {
    const iframeSrc = `${import.meta.env.BASE_URL}frontend/users`
    return { iframeSrc }
  }
}
</script>
