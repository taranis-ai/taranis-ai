<template>
    <v-container>
        <div class="ma-5 pa-5">
            <v-row class="view-panel" dense>
                <slot name="panel"></slot>
            </v-row>
            <v-row class="view-content" dense>
                <slot name="content"></slot>
            </v-row>
        </div>
    </v-container>
    <!-- <v-container fluid class="view">
        <v-row class="view-panel" no-gutters>
            <slot name="panel"></slot>
        </v-row>
        <v-row class="view-content" no-gutters>
            <slot name="content"></slot>
        </v-row>
    </v-container> -->
</template>

<script>
export default {
  name: 'ViewLayout',
  data: () => ({

  }),
  methods: {
  }
}
</script>
