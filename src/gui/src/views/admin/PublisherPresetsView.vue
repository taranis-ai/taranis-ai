<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.publisher_presets' total_count_title="publisher_preset.total_count"
                           total_count_getter="getPublisherPresets">
                <template v-slot:addbutton>
                    <NewPublisherPreset/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name = "PublisherPresets"
                    cardItem="CardPreset"
                    action="getAllPublisherPresets"
                    getter="getPublisherPresets"
                    deletePermission="CONFIG_PUBLISHER_PRESET_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewPublisherPreset from '@/components/config/publisher_presets/NewPublisherPreset'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deletePublisherPreset } from '@/api/config'

export default {
  name: 'PublisherPresets',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewPublisherPreset
  },
  data: () => ({
  }),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deletePublisherPreset(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'publisher_preset.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'publisher_preset.removed_error'
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
