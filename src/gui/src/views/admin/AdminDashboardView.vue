<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Admin Dashboard</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <dash-board-card link-to="/assess" link-text="Assess" cols="4">
        <template #content>
          <v-icon class="mr-2"> mdi-email-multiple-outline </v-icon>
          <span class="caption">
            There are
            <strong>{{ dashboard_data.total_news_items }}</strong> total Assess
            items.
          </span>
        </template>
      </dash-board-card>
      <dash-board-card link-to="/publish" link-text="Publish" cols="4">
        <template #content>
          <v-icon class="mr-2" color="orange"> mdi-email-check-outline </v-icon>
          <span class="caption">
            There are <b>{{ dashboard_data.total_products }}</b> products ready
            for publications.
          </span>
        </template>
      </dash-board-card>
      <dash-board-card link-to="/connectors" link-text="Connectors" cols="4">
        <template #content>
          <v-icon class="mr-2"> mdi-tools </v-icon>
          <span class="caption">
            Here you will find all connectors management tools.
          </span>
        </template>
      </dash-board-card>
    </v-row>
    <v-row no-gutters>
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
      <dash-board-card link-to="/config/workers" link-text="Workers">
        <template #content>
          <v-icon class="mr-2" color="green">
            mdi-lightbulb-off-outline
          </v-icon>
          <span class="caption">
            There are <b>{{ dashboard_data.schedule_length }}</b> tasks
            scheduled
          </span>
          <v-divider inset></v-divider>

          <v-icon class="mr-2"> mdi-clock-check-outline </v-icon>
          <span class="caption">
            Last successful run <b>{{ dashboard_data.latest_collected }}</b>
          </span>
        </template>
      </dash-board-card>
      <dash-board-card link-to="#" link-text="Database">
        <template #content>
          <v-icon class="mr-2" color="blue"> mdi-database-outline </v-icon>
          <span class="caption"
            >There are <b>{{ dashboard_data.total_database_items }}</b> live
            items.</span
          >
          <v-divider inset></v-divider>

          <v-icon class="mr-2"> mdi-database-check-outline </v-icon>
          <span class="caption">There are <b>0</b> archived items.</span>
        </template>
      </dash-board-card>
      <dash-board-card link-text="Build Info" cols="12">
        <template #content>
          <v-row no-gutters>
            <v-col cols="2"> Core Build Time </v-col>
            <v-col cols="2">
              <b>{{ d(coreBuildDate, 'long') }}</b>
            </v-col>
            <v-col v-if="coreGitInfo?.branch" cols="2">
              <b>Branch: {{ coreGitInfo.branch }}</b>
            </v-col>
            <v-col cols="2">
              HEAD:
              <a :href="coreUpstreamTreeUrl">
                {{ coreGitInfo?.HEAD || 'DEV' }}
              </a>
            </v-col>
            <v-divider inset></v-divider>
            <v-col cols="2"> GUI Build Time </v-col>
            <v-col cols="2">
              <b>{{ d(buildDate, 'long') }}</b>
            </v-col>
            <v-col v-if="gitInfo?.branch" cols="2">
              <b>Branch: {{ gitInfo.branch }}</b>
            </v-col>
            <v-col cols="2">
              HEAD:
              <a :href="upstreamTreeUrl">
                {{ gitInfo?.HEAD || 'DEV' }}
              </a>
            </v-col>
          </v-row>
        </template>
      </dash-board-card>
    </v-row>
  </v-container>
</template>

<script>
import { onMounted, ref } from 'vue'
import { useDashboardStore } from '@/stores/DashboardStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { getCoreBuildInfo } from '@/api/dashboard'
import { notifyFailure } from '@/utils/helpers'
import DashBoardCard from '@/components/common/DashBoardCard.vue'

export default {
  name: 'AdminDashboard',
  components: { DashBoardCard },
  setup() {
    const mainStore = useMainStore()
    const dashboardStore = useDashboardStore()
    const { d } = useI18n()

    const { buildDate, gitInfo, upstreamTreeUrl } = storeToRefs(mainStore)
    const { dashboard_data } = storeToRefs(dashboardStore)

    const coreBuildDate = ref(new Date().toISOString())
    const coreGitInfo = ref(null)
    const coreUpstreamTreeUrl = ref(null)

    getCoreBuildInfo().then(
      (response) => {
        coreBuildDate.value = response.data.build_date
        coreGitInfo.value = response.data
        coreUpstreamTreeUrl.value = mainStore.gitUpstreamTreeUrl(response.data)
      },
      (error) => {
        notifyFailure(error)
      }
    )

    onMounted(() => {
      mainStore.drawerVisible = true
      dashboardStore.loadDashboardData()
      mainStore.resetItemCount()
    })

    return {
      coreBuildDate,
      coreGitInfo,
      coreUpstreamTreeUrl,
      upstreamTreeUrl,
      dashboard_data,
      buildDate,
      gitInfo,
      d
    }
  }
}
</script>
