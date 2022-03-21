<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.organizations' total_count_title="organization.total_count"
                           total_count_getter="getOrganizations">
                <template v-slot:addbutton>
                    <NewOrganization/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name = "Organizations"
                    cardItem="CardPreset"
                    action="getAllOrganizations"
                    getter="getOrganizations"
                    deletePermission="CONFIG_ORGANIZATION_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewOrganization from '@/components/config/user/NewOrganization'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deleteOrganization } from '@/api/config'

export default {
  name: 'OrganizationsView',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewOrganization
  },
  data: () => ({
  }),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteOrganization(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'organization.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'organization.removed_error'
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
