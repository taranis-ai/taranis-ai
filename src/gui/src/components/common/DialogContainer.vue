<template>
  <div></div>
</template>

<script>
// import DialogLayout from "../layouts/DialogLayout";

export default {
  name: 'DialogContainer',
  components: {
    // DialogLayout
  },
  props: {},
  data: () => ({
    visible: false,
    title: String
  }),
  mounted() {
    this.$root.$on('callDialog', (e) => {
      this.visible = !this.visible
      this.title = e
    })
  }
}
</script>
