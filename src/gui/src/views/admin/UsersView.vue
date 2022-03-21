<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.users' total_count_title="user.total_count"
                           total_count_getter="getUsers">
                <template v-slot:addbutton>
                    <NewUser/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name = "Users"
                    cardItem="CardUser"
                    action="getAllUsers"
                    getter="getUsers"
                    deletePermission="CONFIG_USER_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewUser from '@/components/config/user/NewUser'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deleteUser } from '@/api/config'

export default {
  name: 'UsersView',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewUser
  },
  data: () => ({
  }),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteUser(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'user.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'user.removed_error'
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
