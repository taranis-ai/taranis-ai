<template>
  <filter-navigation
    :search="productFilter.search"
    :limit="productFilter.limit"
    :offset="productFilter.offset"
    @update:search="(value) => (search = value)"
    @update:limit="(value) => (productFilter.limit = value)"
    @update:offset="(value) => (productFilter.offset = value)"
  >
    <template #navdrawer>
      <v-row class="my-2 mr-0 px-2 pb-5">
        <v-col cols="12" align-self="center" class="py-1">
          <v-btn color="primary" block @click="addProduct()">
            <v-icon left dark> mdi-chart-box-plus-outline </v-icon>
            New Product
          </v-btn>
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>
      <v-row class="my-2 mr-0 px-2">
        <v-col cols="12" class="py-0">
          <h4>Filter</h4>
        </v-col>

        <v-col cols="12" class="pb-0">
          <date-chips v-model="productFilter.range" />
        </v-col>
      </v-row>
    </template>
  </filter-navigation>
</template>

<script>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { usePublishStore } from '@/stores/PublishStore'
import { useFilterStore } from '@/stores/FilterStore'
import FilterNavigation from '@/components/common/FilterNavigation.vue'
import dateChips from '@/components/assess/filter/dateChips.vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import { router } from '@/router'

export default {
  name: 'PublishNav',
  components: {
    dateChips,
    FilterNavigation
  },
  setup() {
    const filterStore = useFilterStore()
    const publishStore = usePublishStore()
    const { productFilter } = storeToRefs(filterStore)
    const { updateProductFilter, setProductFilter } = filterStore
    const updateProducts = publishStore.updateProducts

    const route = useRoute()

    const search = computed({
      get() {
        return productFilter.value.search
      },
      set(value) {
        updateProductFilter({ search: value })
      }
    })

    function addProduct() {
      router.push('/product/0')
    }

    onMounted(() => {
      const query = Object.fromEntries(
        Object.entries(route.query).filter(([, v]) => v != null)
      )
      updateProductFilter(query)
      console.debug('loaded with query', query)
    })

    onUnmounted(() => {
      setProductFilter({})
    })

    watch(
      productFilter,
      (filter, prevFilter) => {
        console.debug('filter changed', filter, prevFilter)
        updateProducts()
      },
      { deep: true }
    )

    return {
      search,
      productFilter,
      updateProductFilter,
      updateProducts,
      addProduct
    }
  }
}
</script>
