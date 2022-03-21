<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title="nav_menu.attributes" total_count_title="attribute.total_count"
                           total_count_getter="getAttributes">
                <template v-slot:addbutton>
                    <NewAttribute/>
                </template>
            </ToolbarFilter>
        </template>
        <template v-slot:content>
            <ContentData
                    name="Attributes"
                    cardItem="CardCompact"
                    action="getAllAttributes"
                    getter="getAttributes"
                    deletePermission="CONFIG_ATTRIBUTE_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import NewAttribute from '../../components/config/attributes/NewAttribute'
import { deleteAttribute } from '../../api/config'

export default {
  name: 'Attributes',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewAttribute
  },
  data: () => ({}),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteAttribute(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'attribute.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'attribute.removed_error'
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
