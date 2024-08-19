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
import { computed, onUnmounted } from 'vue'
import { useFilterStore } from '@/stores/FilterStore'
import FilterNavigation from '@/components/common/FilterNavigation.vue'
import dateChips from '@/components/analyze/dateChips.vue'
import { storeToRefs } from 'pinia'
import { router } from '@/router'

export default {
  name: 'PublishNav',
  components: {
    dateChips,
    FilterNavigation
  },
  setup() {
    const filterStore = useFilterStore()
    const { productFilter } = storeToRefs(filterStore)

    const search = computed({
      get() {
        return productFilter.value.search
      },
      set(value) {
        filterStore.updateProductFilter({ search: value })
      }
    })

    function addProduct() {
      router.push('/product/')
    }

    onUnmounted(() => {
      filterStore.setProductFilter({})
    })

    return {
      search,
      productFilter,
      addProduct
    }
  }
}
</script>
