<template>
  <v-col :cols="cols" class="pa-2 d-flex">
    <v-card class="mx-auto pa-4 dashboard-card w-100">
      <slot name="title">
        <v-card-title>
          <router-link v-if="linkTo != '#'" :to="linkTo">
            {{ linkText }}
          </router-link>
          <span v-else class="title">{{ linkText }}</span>
          <v-divider class="my-2"></v-divider>
        </v-card-title>
      </slot>
      <slot name="card">
        <v-card-text class="pt-0">
          <slot name="content"></slot>
        </v-card-text>
      </slot>
    </v-card>
  </v-col>
</template>

<script>
export default {
  name: 'DashBoardCard',
  props: {
    linkTo: { type: String, default: '#' },
    linkText: { type: String, default: '/' },
    cols: { type: String, default: '4' }
  }
}
</script>

<style lang="scss">
.dashboard-card {
  border: 2px solid white;
  transition: 180ms;
  box-shadow: 1px 2px 9px 0px rgba(0, 0, 0, 0.15);
  flex-grow: 1;
  height: 100%;

  & a {
    color: rgb(var(--v-theme-primary));
  }
}
</style>
