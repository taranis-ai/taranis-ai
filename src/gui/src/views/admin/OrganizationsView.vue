<template>
  <iframe
    :src="iframeSrc"
    title="Organizations"
    class="frontend-iframe"
  ></iframe>
</template>

<script>
export default {
  name: 'OrganizationsView',
  setup() {
    const iframeSrc = `${import.meta.env.BASE_URL}frontend/organizations`
    return { iframeSrc }
  }
}
</script>
