<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.presenters_nodes' total_count_title="presenters_node.total_count"
                           total_count_getter="getPresentersNodes">
                <template v-slot:addbutton>
                    <NewPresentersNode/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name="PresentersNodes"
                    cardItem="CardNode"
                    action="getAllPresentersNodes"
                    getter="getPresentersNodes"
                    deletePermission="CONFIG_PRESENTERS_NODE_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewPresentersNode from '@/components/config/presenters_nodes/NewPresentersNode'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deletePresentersNode } from '@/api/config'

export default {
  name: 'PresentersNodes',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewPresentersNode
  },
  data: () => ({}),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deletePresentersNode(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'presenters_node.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'presenters_node.removed_error'
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
