<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.remote_nodes' total_count_title="remote_node.total_count"
                           total_count_getter="getRemoteNodes">
                <template v-slot:addbutton>
                    <NewRemoteNode/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name="RemoteNodes"
                    cardItem="CardPreset"
                    action="getAllRemoteNodes"
                    getter="getRemoteNodes"
                    deletePermission="CONFIG_REMOTE_NODE_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewRemoteNode from '@/components/config/remote/NewRemoteNode'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deleteRemoteNode } from '@/api/config'

export default {
  name: 'RemoteNodes',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewRemoteNode
  },
  data: () => ({}),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteRemoteNode(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'remote_node.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'remote_node.removed_error'
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
