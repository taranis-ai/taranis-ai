<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.publishers_nodes' total_count_title="publishers_node.total_count"
                           total_count_getter="getPublishersNodes">
                <template v-slot:addbutton>
                    <NewPublishersNode/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name="PublishersNodes"
                    cardItem="CardNode"
                    action="getAllPublishersNodes"
                    getter="getPublishersNodes"
                    deletePermission="CONFIG_PUBLISHERS_NODE_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewPublishersNode from '@/components/config/publishers_nodes/NewPublishersNode'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deletePublishersNode } from '@/api/config'

export default {
  name: 'PublishersNodes',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewPublishersNode
  },
  data: () => ({}),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deletePublishersNode(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'publisher_node.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'publisher_node.removed_error'
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
