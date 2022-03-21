<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.bots_nodes' total_count_title="bots_node.total_count"
                           total_count_getter="getBotsNodes">
                <template v-slot:addbutton>
                    <NewBotsNode/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name="BotsNodes"
                    cardItem="CardNode"
                    action="getAllBotsNodes"
                    getter="getBotsNodes"
                    deletePermission="CONFIG_BOTS_NODE_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewBotsNode from '@/components/config/bots_nodes/NewBotsNode'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deleteBotsNode } from '@/api/config'

export default {
  name: 'BotsNodes',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewBotsNode
  },
  data: () => ({}),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteBotsNode(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'bots_node.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'bots_node.removed_error'
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
