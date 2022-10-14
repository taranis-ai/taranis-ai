<template>
  <ViewLayout>
    <template v-slot:panel>
      <ToolbarFilter title='nav_menu.nodes' total_count_title="nodes.total_count"
                      total_count_getter="config/getNodes">
        <template v-slot:addbutton>
          <EditNode/>
        </template>

      </ToolbarFilter>

    </template>
    <template v-slot:content>
        <ContentData
                name="CollectorsNodes"
                cardItem="CardNode"
                action="config/loadCollectorsNodes"
                getter="config/getCollectorsNodes"
                deletePermission="CONFIG_COLLECTORS_NODE_DELETE"
        />
        <ContentData
                name="BotsNodes"
                cardItem="CardNode"
                action="config/getAllBotsNodes"
                getter="config/getBotsNodes"
                deletePermission="CONFIG_BOTS_NODE_DELETE"
        />
        <ContentData
                name="PublishersNodes"
                cardItem="CardNode"
                action="config/getAllPublishersNodes"
                getter="config/getPublishersNodes"
                deletePermission="CONFIG_PUBLISHERS_NODE_DELETE"
        />
        <ContentData
                name="PresentersNodes"
                cardItem="CardNode"
                action="config/loadPresentersNodes"
                getter="config/getPresentersNodes"
                deletePermission="CONFIG_PRESENTERS_NODE_DELETE"
        />
    </template>
  </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import ToolbarFilter from '../../components/common/ToolbarFilter'
import EditNode from '../../components/config/nodes/EditNode'
import ContentData from '../../components/common/content/ContentData'
import { mapActions } from 'vuex'

export default {
  name: 'Nodes',
  components: {
    ViewLayout,
    ToolbarFilter,
    ContentData,
    EditNode
  },
  methods: {
    ...mapActions('config', [
      'getAllNodes'
    ])
  },
  data: () => ({}),
  mounted () {
    var filter = { search: '' }
    this.getAllNodes(filter)
  },
  beforeDestroy () {
    this.$root.$off('delete-item')
  }
}

</script>
