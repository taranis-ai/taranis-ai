<template>
  <v-container fluid style="min-height: 100vh">
    {{ asset }}
  </v-container>
</template>

<script>
import { getAsset } from '@/api/assets'
import { notifySuccess } from '@/utils/helpers'

export default {
  name: 'AssetGroup',
  data: () => ({
    default_asset: {
      id: null,
      name: '',
      description: ''
    },
    asset: undefined,
    edit: true
  }),
  components: { },
  mounted() {
    this.asset = this.default_asset
  },
  async created() {
    this.asset = await this.loadAsset()
    if (this.asset === undefined) {
      this.asset = this.default_asset
      this.edit = false
    }
  },
  methods: {
    async loadAsset() {
      if (this.$route.params.id && this.$route.params.id !== '0') {
        return await getAsset(this.$route.params.id).then((response) => {
          return response.data
        })
      }
    },
    reportCreated(asset) {
      notifySuccess(`Asset with ID ${asset} created`)
      this.edit = true
    }
  }
}
</script>
