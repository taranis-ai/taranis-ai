<template>
  <v-container fluid style="min-height: 100vh">
    <asset
      v-if="readyToRender"
      :edit="edit"
      :asset-prop="asset"
      @assetcreated="assetcreated"
    />
  </v-container>
</template>

<script>
import { ref, onMounted } from 'vue'
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

    const default_asset = ref({
      name: '',
      serial: '',
      description: '',
      asset_cpes: [],
      group: null
    })
    const asset = ref(default_asset.value)
    const edit = ref(true)
    const readyToRender = ref(false)

    const loadAsset = async () => {
      if (route.params.id && route.params.id !== '0') {
        const response = await getAsset(this.$route.params.id)
        return response.data
      } else {
        edit.value = false
        return default_asset.value
      }
    }

    const assetcreated = (asset) => {
      notifySuccess(`Asset with ID ${asset} created`)
      edit.value = true
    }

    onMounted(async () => {
      asset.value = await loadAsset()
      readyToRender.value = true
    })

    return {
      asset,
      edit,
      readyToRender,
      assetcreated
    }
  }
}
</script>
