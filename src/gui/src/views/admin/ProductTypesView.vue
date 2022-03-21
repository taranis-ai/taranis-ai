<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.product_types' total_count_title="product_type.total_count"
                           total_count_getter="getProductTypes">
                <template v-slot:addbutton>
                    <NewProductType/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name = "ProductTypes"
                    cardItem="CardProductType"
                    action="getAllProductTypes"
                    getter="getProductTypes"
                    deletePermission="CONFIG_PRODUCT_TYPE_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewProductType from '@/components/config/product_types/NewProductType'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deleteProductType } from '@/api/config'

export default {
  name: 'ProductTypes',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewProductType
  },
  data: () => ({
  }),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteProductType(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'product_type.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'product_type.removed_error'
          }
        )
      })
    })
  },
  beforeDestroy () {
    this.$root.$off('delete-item')
  }
}

</script>
