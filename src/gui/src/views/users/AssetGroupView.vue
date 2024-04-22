<template>
  <v-container fluid>
    <asset-group
      :edit="edit"
      :asset-group-prop="assetGroup"
      @assetcreated="assetcreated"
    />
  </v-container>
</template>

<script>
import { getAssetGroup } from '@/api/assets'
import { notifySuccess } from '@/utils/helpers'
import AssetGroup from '@/components/assets/AssetGroup.vue'
import { ref, onBeforeMount } from 'vue'
import { useRoute } from 'vue-router'

export default {
  name: 'AssetGroupView',
  components: {
    AssetGroup
  },
  setup() {
    const route = useRoute()
    const edit = ref(true)
    const defaultAssetGroup = ref({
      name: '',
      description: ''
    })
    const assetGroup = ref(defaultAssetGroup.value)

    const loadAssetGroup = async () => {
      if (route.params.id) {
        const response = await getAssetGroup(route.params.id)
        return response.data
      } else {
        edit.value = false
        return defaultAssetGroup.value
      }
    }

    const assetcreated = (asset) => {
      notifySuccess(`Asset Group with ID ${asset} created`)
      edit.value = true
    }

    onBeforeMount(async () => {
      assetGroup.value = await loadAssetGroup()
    })

    return {
      assetGroup,
      edit,
      assetcreated
    }
  }
}
</script>
