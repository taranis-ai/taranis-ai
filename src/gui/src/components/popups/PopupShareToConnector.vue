<template>
  <v-card>
    <v-card-title> Share to a connected instance </v-card-title>
    <v-card-text>
      Select a connector:
      <v-autocomplete
        v-model="connectorSelection"
        :items="connectors"
        item-title="name"
        item-value="id"
        single-line
        label="Select Connector"
        no-data-text="No connectors found"
        menu-icon="mdi-chevron-down"
      />
      <v-spacer />
    </v-card-text>
    <v-card-actions class="mt-1">
      <v-btn
        variant="outlined"
        class="text-lowercase text-red-darken-3 ml-3"
        prepend-icon="mdi-close"
        @click="close"
      >
        Abort
      </v-btn>
      <v-spacer />
      <v-btn
        variant="outlined"
        class="text-lowercase text-primary mr-3"
        prepend-icon="mdi-share-outline"
        @click="share"
      >
        Share with Connector
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
<script>
import { shareToConnector } from '@/api/assess'
import { useConfigStore } from '@/stores/ConfigStore'
import { ref, onMounted } from 'vue'
export default {
  name: 'PopupShareToConnector',
  props: {
    itemIds: {
      type: Array,
      default: () => []
    },
    dialog: Boolean
  },
  emits: ['close'],
  setup(props, { emit }) {
    const configStore = useConfigStore()
    const connectors = ref([])
    const connectorSelection = ref(null)

    const share = () => {
      if (connectorSelection.value && props.itemIds.length > 0) {
        shareToConnector(connectorSelection.value, props.itemIds)
        emit('close')
      }
    }

    const close = () => {
      emit('close')
    }

    onMounted(() => {
      configStore.loadConnectors().then(() => {
        connectors.value = configStore.connectors.items
      })
    })

    return {
      connectorSelection,
      connectors,
      share,
      close
    }
  }
}
</script>
