<template>
  <div>
    <ConfigTable :items="osint_source_groups" />
  </div>
</template>

<script>
import ConfigTable from '../../components/config/ConfigTable'

import { deleteOSINTSourceGroup } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'OSINTSourceGroups',
  components: {
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
