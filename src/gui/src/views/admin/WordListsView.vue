<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title="nav_menu.word_lists" total_count_title="word_list.total_count"
                           total_count_getter="getWordLists">
                <template v-slot:addbutton>
                    <NewWordList/>
                </template>
            </ToolbarFilter>
        </template>
        <template v-slot:content>
            <ContentData
                    name="WordLists"
                    cardItem="CardCompact"
                    action="getAllWordLists"
                    getter="getWordLists"
                    deletePermission="CONFIG_WORD_LIST_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import ContentData from '../../components/common/content/ContentData'
import NewWordList from '../../components/config/word_lists/NewWordList'
import { deleteWordList } from '@/api/config'

export default {
  name: 'WordLists',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    NewWordList
  },
  data: () => ({}),
  mounted () {
    this.$root.$on('delete-item', (item) => {
      deleteWordList(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: 'word_list.removed'
          }
        )
      }).catch(() => {
        this.$root.$emit('notification',
          {
            type: 'error',
            loc: 'word_list.removed_error'
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
