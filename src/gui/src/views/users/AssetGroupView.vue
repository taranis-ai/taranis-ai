<template>
  <v-container fluid style="min-height: 100vh">
    <asset-group
      v-if="asset"
      v-model:edit="edit"
      :asset-group-prop="asset"
      @assetcreated="assetcreated"
    />
  </v-container>
</template>

<script>
import { getAssetGroup } from '@/api/assets'
import { notifySuccess } from '@/utils/helpers'
import AssetGroup from '@/components/assets/AssetGroup.vue'

export default {
  name: 'AssetGroupView',
  components: {
    AssetGroup
  },
  data: function () {
    return {
      default_asset: {
        name: '',
        description: ''
      },
      asset: undefined,
      edit: true
    }
  },
  async created() {
    this.asset = await this.loadAsset()
  },
  methods: {
    async loadAsset() {
      if (this.$route.params.id && this.$route.params.id !== '0') {
        return await getAssetGroup(this.$route.params.id).then((response) => {
          return response.data
        })
      }
      this.edit = false
      return this.default_asset
    },
    assetcreated(asset) {
      notifySuccess(`Asset with ID ${asset} created`)
      this.edit = true
    }
  }
}
</script>
