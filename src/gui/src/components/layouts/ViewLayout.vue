<template>
  <div>
    <v-container fluid class="ma-0 pa-0" style="width: 100%">
      <v-row class="view-panel" dense>
        <slot name="panel"></slot>
      </v-row>
    </v-container>
    <v-container>
      <div class="ma-5 mt-5 pa-5 pt-0">
        <v-row class="view-content" dense>
          <slot name="content"></slot>
        </v-row>
      </div>
    </v-container>
  </div>
</template>

<script>
export default {
  name: 'ViewLayout',
  data: () => ({}),
  methods: {}
}
</script>
