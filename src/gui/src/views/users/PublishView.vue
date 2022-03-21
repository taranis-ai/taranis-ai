<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilterPublish title='nav_menu.products' total_count_title="product.total_count">
                <template v-slot:addbutton>
                    <NewProduct add_button/>
                </template>
            </ToolbarFilterPublish>
        </template>
        <template v-slot:content>
            <ContentDataPublish/>
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import ToolbarFilterPublish from '../../components/publish/ToolbarFilterPublish'
import ContentDataPublish from '../../components/publish/ContentDataPublish'
import NewProduct from '@/components/publish/NewProduct'
import { deleteProduct } from '@/api/publish'

export default {
  name: 'Publish',
  components: {
    ViewLayout,
    ToolbarFilterPublish,
    ContentDataPublish,
    NewProduct
  },
  mounted () {
    this.$root.$on('delete-product', (item) => {
      deleteProduct(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'product.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'product.removed_error'
          }
        )
      })
    })
  },
  beforeDestroy () {
    this.$root.$off('delete-product')
  }
}
</script>
