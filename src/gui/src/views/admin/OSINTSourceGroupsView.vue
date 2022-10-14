<template>
  <ViewLayout>
    <template v-slot:content>
      <v-layout child-flex>
      <ConfigTable :items="osint_source_groups" />
    </v-layout>
    </template>
  </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import ConfigTable from '../../components/config/ConfigTable'

import { deleteOSINTSourceGroup } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'OSINTSourceGroups',
  components: {
    ViewLayout,
    ConfigTable
  },
  data: () => ({
    osint_source_groups: []
  }),
  methods: {
    ...mapGetters('config', ['getOSINTSourceGroups']),
    ...mapActions('config', ['loadOSINTSourceGroups']),
    ...mapGetters('assess', ['getOSINTSourceGroupList']),
    ...mapActions('assess', ['updateOSINTSourceGroupsList']),
    deleteItem(item) {
      if (!item.default) {
        deleteOSINTSourceGroup(item)
      }
    }
  },
  mounted () {
    this.updateOSINTSourceGroupsList().then(() => {
      this.osint_source_groups = this.getOSINTSourceGroupList().items
    })
  },
  beforeDestroy () {
    this.$root.$off('delete-item')
  }
}

</script>
