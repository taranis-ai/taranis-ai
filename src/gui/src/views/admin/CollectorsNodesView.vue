<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.collectors_nodes' total_count_title="collectors_node.total_count"
                           total_count_getter="getCollectorsNodes">
                <template v-slot:addbutton>
                    <NewCollectorsNode/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name="CollectorsNodes"
                    cardItem="CardNode"
                    action="getAllCollectorsNodes"
                    getter="getCollectorsNodes"
                    deletePermission="CONFIG_COLLECTORS_NODE_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewCollectorsNode from '../../components/config/collectors_nodes/NewCollectorsNode'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deleteCollectorsNode } from '@/api/config'

export default {
  name: 'CollectorsNodes',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewCollectorsNode
  },
  data: () => ({}),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteCollectorsNode(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'collectors_node.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'collectors_node.removed_error'
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
