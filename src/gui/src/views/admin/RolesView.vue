<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.roles' total_count_title="role.total_count"
                           total_count_getter="getRoles">
                <template v-slot:addbutton>
                    <NewRole/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name = "Roles"
                    cardItem="CardPreset"
                    action="getAllRoles"
                    getter="getRoles"
                    deletePermission="CONFIG_ROLE_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewRole from '@/components/config/user/NewRole'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deleteRole } from '@/api/config'

export default {
  name: 'RolesView',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewRole
  },
  data: () => ({
  }),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteRole(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'role.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'role.removed_error'
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
