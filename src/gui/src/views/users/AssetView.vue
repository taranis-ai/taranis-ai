<template>
  <v-container fluid>
    <asset :edit="edit" :asset-prop="asset" @assetcreated="assetcreated" />
  </v-container>
</template>

<script>
import { ref, onBeforeMount } from 'vue'
import { getAsset } from '@/api/assets'
import { notifySuccess } from '@/utils/helpers'
import Asset from '@/components/assets/Asset.vue'
import { useRoute } from 'vue-router'

export default {
  name: 'AssetView',
  components: {
    Asset
  },
  setup() {
    const route = useRoute()

    const defaultAsset = ref({
      name: '',
      serial: '',
      description: '',
      asset_cpes: [],
      group: null
    })
    const asset = ref(defaultAsset.value)
    const edit = ref(true)

    const loadAsset = async () => {
      if (route.params.id) {
        const response = await getAsset(route.params.id)
        return response.data
      } else {
        edit.value = false
        return defaultAsset.value
      }
    }

    const assetcreated = (asset) => {
      notifySuccess(`Asset with ID ${asset} created`)
      edit.value = true
    }

    onBeforeMount(async () => {
      asset.value = await loadAsset()
    })

    return {
      asset,
      edit,
      assetcreated
    }
  }
}
</script>
