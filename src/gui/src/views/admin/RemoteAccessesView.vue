<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.remote_access' total_count_title="remote_access.total_count"
                           total_count_getter="getRemoteAccesses">
                <template v-slot:addbutton>
                    <NewRemoteAccess/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name="RemoteAccesses"
                    cardItem="CardPreset"
                    action="getAllRemoteAccesses"
                    getter="getRemoteAccesses"
                    deletePermission="CONFIG_REMOTE_ACCESS_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewRemoteAccess from '@/components/config/remote/NewRemoteAccess'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deleteRemoteAccess } from '@/api/config'

export default {
  name: 'RemoteAccesses',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewRemoteAccess
  },
  data: () => ({}),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteRemoteAccess(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'remote_access.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'remote_access.removed_error'
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
