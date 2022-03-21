<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='acl.full_title' total_count_title="acl.total_count"
                           total_count_getter="getACLEntries">
                <template v-slot:addbutton>
                    <NewACL/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name = "ACLEntries"
                    cardItem="CardPreset"
                    action="getAllACLEntries"
                    getter="getACLEntries"
                    deletePermission="CONFIG_ACL_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewACL from '@/components/config/user/NewACL'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deleteACLEntry } from '@/api/config'

export default {
  name: 'ACLEntriesView',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewACL
  },
  data: () => ({
  }),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteACLEntry(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'acl.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'acl.removed_error'
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
