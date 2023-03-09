<template>
  <v-container fluid style="min-height: 100vh">
    <asset
      v-if="asset"
      :asset_prop="asset"
      :edit.sync="edit"
      @assetcreated="assetcreated"
    />
  </v-container>
</template>

<script>
import { getAssetGroup } from '@/api/assets'
import { notifySuccess } from '@/utils/helpers'
import Asset from '@/components/assets/Asset'

export default {
  name: 'AssetGroupView',
  data: function () {
    return {
      default_asset: {
        id: -1,
        name: '',
        description: ''
      },
      asset: undefined,
      edit: true
    }
  },
  components: {
    Asset
  },
  async created() {
    console.debug('AssetGroupView created')
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
