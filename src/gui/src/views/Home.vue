<template>
  <v-container fluid>
    <v-row no-gutters align="center" justify="center">
      <v-btn-toggle
        v-model="trendingClusterScope"
        class="mb-1"
        variant="tonal"
        selected-class="active-toggle"
        mandatory
        @update:model-value="toggleScope"
      >
        <v-btn value="0">
          <v-tooltip activator="parent">Complete Database</v-tooltip>
          All
        </v-btn>
        <v-btn value="2">
          <v-tooltip activator="parent">Last 2 days</v-tooltip>
          Trending
        </v-btn>
        <v-btn value="7">
          <v-tooltip activator="parent">Last 7 days</v-tooltip>
          Ongoing
        </v-btn>
      </v-btn-toggle>
    </v-row>
    <v-row no-gutters>
      <dash-board-card v-for="(cluster, name) in clusters" :key="name">
        <template #title>
          <v-card-title>
            <v-divider />
          </v-card-title>
        </template>
        <template #card>
          <trending-card :cluster="cluster" :tag-type="name" />
        </template>
      </dash-board-card>

      <dash-board-card link-to="/assess" link-text="Assess">
        <template #content>
          <v-icon class="mr-2"> mdi-email-multiple-outline </v-icon>
          <span class="caption">
            There are
            <strong>{{ dashboard_data.total_news_items }}</strong> total Assess
            items.
          </span>
        </template>
      </dash-board-card>
      <dash-board-card link-to="/analyze" link-text="Analyze">
        <template #content>
          <v-icon class="mr-2"> mdi-account-outline </v-icon>
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
      <dash-board-card link-to="/connectors" link-text="Connectors">
        <template #content>
          <v-icon class="mr-2"> mdi-tools </v-icon>
          <span class="caption">
            There are <b>{{ dashboard_data.conflict_count }}</b> conflicts
            detected.
          </span>
          <v-divider inset></v-divider>
          <v-icon class="mr-2"> mdi-tools </v-icon>
          <span class="caption">
            Here you can find all connectors management tools. There are
            <b>{{ dashboard_data.conflict_count }}</b> conflicts detected.
          </span>
        </template>
      </dash-board-card>
    </v-row>
  </v-container>
</template>

<script>
import DashBoardCard from '@/components/common/DashBoardCard.vue'
import TrendingCard from '@/components/common/TrendingCard.vue'
import { useDashboardStore } from '@/stores/DashboardStore'
import { useMainStore } from '@/stores/MainStore'
import { onMounted, defineComponent, ref } from 'vue'
import { storeToRefs } from 'pinia'

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
    const trendingClusterScope = ref('7')

    function toggleScope() {
      dashboardStore.loadClusters(trendingClusterScope.value)
    }

    onMounted(() => {
      dashboardStore.loadDashboardData()
      dashboardStore.loadClusters(trendingClusterScope.value)
      mainStore.resetItemCount()
    })
    return {
      trendingClusterScope,
      dashboard_data,
      clusters,
      toggleScope
    }
  }
})
</script>

<style>
.active-toggle.v-btn--active {
  background-color: rgb(var(--v-theme-primary));
  color: white;
  border: none;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
