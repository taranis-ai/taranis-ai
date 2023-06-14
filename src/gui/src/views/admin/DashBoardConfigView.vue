<template>
  <v-container fluid>
    <v-row no-gutters>
      <dash-board-card link-to="/assess" link-text="Assess" cols="6">
        <template #content>
          <v-icon class="mr-2"> mdi-email-multiple </v-icon>
          <span class="caption">
            There are
            <strong>{{ dashboard_data.total_news_items }}</strong> total Assess
            items.
          </span>
        </template>
      </dash-board-card>
      <dash-board-card link-to="/publish" link-text="Publish" cols="6">
        <template #content>
          <v-icon class="mr-2" color="orange"> mdi-email-check-outline </v-icon>
          <span class="caption">
            There are <b>{{ dashboard_data.total_products }}</b> products ready
            for publications.
          </span>
        </template>
      </dash-board-card>
    </v-row>
    <v-row no-gutters>
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
      <dash-board-card link-to="/config/nodes" link-text="Nodes">
        <template #content>
          <v-icon class="mr-2" color="green">
            mdi-lightbulb-off-outline
          </v-icon>
          <span class="caption">Collectors are pending</span>
          <v-divider inset></v-divider>

          <v-icon class="mr-2"> mdi-clock-check-outline </v-icon>
          <span class="caption"
            >Last successful run ended at
            <b>{{ dashboard_data.latest_collected }}</b></span
          >
        </template>
      </dash-board-card>
      <dash-board-card link-to="#" link-text="Database">
        <template #content>
          <v-icon class="mr-2" color="blue"> mdi-database </v-icon>
          <span class="caption"
            >There are <b>{{ dashboard_data.total_database_items }}</b> live
            items.</span
          >
          <v-divider inset></v-divider>

          <v-icon class="mr-2"> mdi-database-check </v-icon>
          <span class="caption">There are <b>0</b> archived items.</span>
        </template>
      </dash-board-card>
    </v-row>
  </v-container>
</template>

<script>
import { onMounted } from 'vue'
import { useDashboardStore } from '@/stores/DashboardStore'
import { useMainStore } from '@/stores/MainStore'
import DashBoardCard from '@/components/common/DashBoardCard.vue'
import { storeToRefs } from 'pinia'

export default {
  name: 'DashBoardConfig',
  components: { DashBoardCard },
  setup() {
    const mainStore = useMainStore()
    const dashboardStore = useDashboardStore()

    const { dashboard_data } = storeToRefs(dashboardStore)

    onMounted(() => {
      dashboardStore.loadDashboardData()
      mainStore.resetItemCount()
    })

    return {
      dashboard_data
    }
  }
}
</script>
