<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.bot_presets' total_count_title="bot_preset.total_count"
                           total_count_getter="getBotPresets">
                <template v-slot:addbutton>
                    <NewBotPreset/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name = "BotPresets"
                    cardItem="CardPreset"
                    action="getAllBotPresets"
                    getter="getBotPresets"
                    deletePermission="CONFIG_BOT_PRESET_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import NewBotPreset from '@/components/config/bot_presets/NewBotPreset'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import { deleteBotPreset } from '@/api/config'

export default {
  name: 'BotPresets',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewBotPreset
  },
  data: () => ({
  }),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteBotPreset(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'bot_preset.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'bot_preset.removed_error'
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
