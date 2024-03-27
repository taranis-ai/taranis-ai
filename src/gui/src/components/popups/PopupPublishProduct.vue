<template>
  <v-card>
    <v-card-title> Publish Product </v-card-title>
    <v-card-subtitle style="background-color: #ffff00">
      !!! EARLY ACCESS MIGHT NOT WORK !!!
    </v-card-subtitle>
    <v-card-text>
      Select a publisher:
      <v-select
        v-model="publisherSelection"
        :items="publisher"
        item-title="name"
        item-value="id"
        :label="$t('product.publisher')"
      />
    </v-card-text>
    <v-card-actions class="mt-1">
      <v-btn
        variant="outlined"
        class="text-lowercase text-red-darken-3 ml-3"
        prepend-icon="mdi-close"
        @click="close()"
      >
        abort
      </v-btn>
      <v-spacer></v-spacer>
      <v-btn
        variant="outlined"
        class="text-lowercase text-primary mr-3"
        prepend-icon="mdi-share-outline"
        @click="publish()"
      >
        publish
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { publishProduct } from '@/api/publish'
import { useConfigStore } from '@/stores/ConfigStore'
import { ref, onMounted, computed } from 'vue'

export default {
  name: 'PopupPublishProduct',
  props: {
    productId: {
      type: Number,
      required: true
    },
    dialog: Boolean
  },
  emits: ['close'],
  setup(props, { emit }) {
    const publisherSelection = ref(null)
    const configStore = useConfigStore()

    const publisher = computed(() => {
      return configStore.publisher.items
    })

    const publish = () => {
      publishProduct(props.productId, publisherSelection.value)
      emit('close')
    }

    const close = () => {
      emit('close')
    }

    onMounted(() => {
      configStore.loadPublisher()
    })

    return {
      publisher,
      publisherSelection,
      publish,
      close
    }
  }
}
</script>
