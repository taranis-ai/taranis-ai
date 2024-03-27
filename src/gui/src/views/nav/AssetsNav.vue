<template>
  <filter-navigation
    :search="assetFilter.search"
    :limit="limit"
    :offsest="offset"
    @update:search="(value) => (search = value)"
    @update:limit="(value) => (limit = value)"
    @update:offset="(value) => (offset = value)"
  >
    <template #navdrawer>
      <v-row class="my-2 mr-0 px-2 pb-5">
        <v-col cols="12" align-self="center" class="py-1">
          <v-btn color="primary" block @click="addAsset()">
            <v-icon left dark> mdi-view-grid-plus </v-icon>
            New Asset
          </v-btn>
        </v-col>
        <v-col cols="12" align-self="center" class="py-2">
          <v-btn color="primary" block @click="addAssetGroup()">
            <v-icon left dark> mdi-folder-plus-outline </v-icon>
            New Asset Group
          </v-btn>
        </v-col>
      </v-row>
    </template>
  </filter-navigation>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAssetsStore } from '@/stores/AssetsStore'
import { useFilterStore } from '@/stores/FilterStore'
import FilterNavigation from '@/components/common/FilterNavigation.vue'
import { storeToRefs } from 'pinia'

export default {
  name: 'AssetsNav',
  components: {
    FilterNavigation
  },
  setup() {
    const filterStore = useFilterStore()
    const assetsStore = useAssetsStore()

    const { assetFilter } = storeToRefs(filterStore)

    const route = useRoute()
    const router = useRouter()

    const limit = computed({
      get() {
        return assetFilter.value.limit
      },
      set(value) {
        filterStore.updateAssetFilter({ limit: value })
        assetsStore.updateFilteredAssets()
      }
    })

    const sort = computed({
      get() {
        if (!assetFilter.value.order) return 'DATE_DESC'
        return assetFilter.value.order
      },
      set(value) {
        filterStore.updateAssetFilter({ sort: value })
        assetsStore.updateFilteredAssets()
      }
    })

    const offset = computed({
      get() {
        return assetFilter.value.offset
      },
      set(value) {
        filterStore.updateAssetFilter({ offset: value })
        assetsStore.updateFilteredAssets()
      }
    })

    const search = ref(assetFilter.value.search)
    const awaitingSearch = ref(false)

    const addAsset = () => {
      router.push('/asset/')
    }

    const addAssetGroup = () => {
      router.push('/asset-group/')
    }

    const updateSearch = (value) => {
      search.value = value
      filterStore.updateAssetFilter({ search: value })
      if (!awaitingSearch.value) {
        setTimeout(() => {
          updateFilteredAssets()
          awaitingSearch.value = false
        }, 500)
      }
      awaitingSearch.value = true
    }

    onMounted(() => {
      const query = Object.fromEntries(
        Object.entries(route.query).filter(([, v]) => v != null)
      )
      filterStore.updateAssetFilter(query)
    })

    return {
      assetFilter,
      limit,
      sort,
      offset,
      search,
      awaitingSearch,
      addAsset,
      addAssetGroup,
      updateSearch
    }
  }
}
</script>
