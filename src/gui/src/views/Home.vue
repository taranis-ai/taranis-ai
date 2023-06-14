<template>
  <v-container fluid>
    <v-row no-gutters>
      <dash-board-card
        v-for="cluster in clusters"
        :key="cluster.name"
        :link-to="`/assess?tags=${cluster.name}`"
        :link-text="cluster.name"
      >
        <template #card>
          <trending-card :cluster="cluster" />
        </template>
      </dash-board-card>

      <dash-board-card link-to="/assess" link-text="Assess">
        <template #content>
          <v-icon class="mr-2"> mdi-email-multiple </v-icon>
          <span class="caption">
            There are
            <strong>{{ dashboard_data.total_news_items }}</strong> total Assess
            items.
          </span>
        </template>
      </dash-board-card>
      <dash-board-card link-to="/analyze" link-text="Analyze">
        <template #content>
          <v-icon class="mr-2"> mdi-account </v-icon>
          <span class="caption">
            There are <b>{{ dashboard_data.report_items_completed }}</b>
            completed analyses.
          </span>
          <v-divider inset></v-divider>
          <v-icon class="mr-2" color="grey">
            mdi-account-question-outline
          </v-icon>
          <span class="caption">
            There are <b>{{ dashboard_data.report_items_in_progress }}</b>
            pending analyses.
          </span>
        </template>
      </dash-board-card>
      <dash-board-card link-to="/publish" link-text="Publish">
        <template #content>
          <v-icon class="mr-2" color="orange"> mdi-email-check-outline </v-icon>
          <span class="caption">
            There are <b>{{ dashboard_data.total_products }}</b> products ready
            for publications.
          </span>
        </template>
      </dash-board-card>
    </v-row>
  </v-container>
</template>

<script>
import DashBoardCard from '@/components/common/DashBoardCard.vue'
import { onMounted } from 'vue'
import TrendingCard from '@/components/common/TrendingCard.vue'
import { defineComponent } from 'vue'
import { useDashboardStore } from '@/stores/DashboardStore'
import { storeToRefs } from 'pinia'
import { useMainStore } from '@/stores/MainStore'

export default defineComponent({
  name: 'HomeView',
  components: {
    DashBoardCard,
    TrendingCard
  },
  setup() {
    const mainStore = useMainStore()
    const dashboardStore = useDashboardStore()
    const { dashboard_data, clusters } = storeToRefs(dashboardStore)

    onMounted(() => {
      dashboardStore.loadDashboardData()
      dashboardStore.loadClusters()
      mainStore.resetItemCount()
    })
    return {
      dashboard_data,
      clusters
    }
  }
})
</script>
