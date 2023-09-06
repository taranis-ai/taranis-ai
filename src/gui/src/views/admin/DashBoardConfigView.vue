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
      <dash-board-card link-to="/config/workers" link-text="Workers">
        <template #content>
          <v-icon class="mr-2" color="green">
            mdi-lightbulb-off-outline
          </v-icon>
          <span class="caption"
            >Tasks are scheduled
            <b>{{ schedule_length }}</b>
          </span>
          <v-divider inset></v-divider>

          <v-icon class="mr-2"> mdi-clock-check-outline </v-icon>
          <span class="caption"
            >Last successful run
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
      <dash-board-card link-text="Build Info" cols="12">
        <template #content>
          <v-row no-gutters>
            <v-col cols="2"> Core Build Time </v-col>
            <v-col cols="2" offset="1">
              <b>{{ d(coreBuildDate, 'long') }}</b>
            </v-col>
            <v-col cols="2" offset="1">
              <b>Branch: {{ coreGitInfo.branch }}</b>
            </v-col>
            <v-col cols="2" offset="1">
              <b v-if="coreGitInfo.TAG">Tag: {{ coreGitInfo.branch }}</b>
              <b v-else>HEAD: {{ coreGitInfo.HEAD }}</b>
            </v-col>
            <v-divider inset></v-divider>
            <v-col cols="2"> GUI Build Time </v-col>
            <v-col cols="2" offset="1">
              <b>{{ d(buildDate, 'long') }}</b>
            </v-col>
            <v-col cols="2" offset="1">
              <b>Branch: {{ gitInfo.branch }}</b>
            </v-col>
            <v-col cols="2" offset="1">
              <b v-if="gitInfo.TAG">Tag: {{ gitInfo.branch }}</b>
              <b v-else>HEAD: {{ gitInfo.HEAD }}</b>
            </v-col>
          </v-row>
        </template>
      </dash-board-card>
    </v-row>
  </v-container>
</template>

<script>
import { onMounted, ref, computed } from 'vue'
import { useDashboardStore } from '@/stores/DashboardStore'
import { useMainStore } from '@/stores/MainStore'
import { useConfigStore } from '@/stores/ConfigStore'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { getCoreBuildInfo } from '@/api/dashboard'
import { notifyFailure } from '@/utils/helpers'
import DashBoardCard from '@/components/common/DashBoardCard.vue'

export default {
  name: 'DashBoardConfig',
  components: { DashBoardCard },
  setup() {
    const mainStore = useMainStore()
    const dashboardStore = useDashboardStore()
    const configStore = useConfigStore()
    const { d } = useI18n()

    mainStore.updateFromLocalConfig()

    const { buildDate, gitInfo } = storeToRefs(mainStore)
    const { dashboard_data } = storeToRefs(dashboardStore)
    const schedule_length = computed(() => configStore.schedule.length ?? 0)

    const coreBuildDate = ref(new Date().toISOString())
    const coreGitInfo = ref('')

    getCoreBuildInfo().then(
      (response) => {
        coreBuildDate.value = response.data.build_date
        coreGitInfo.value = response.data
      },
      (error) => {
        notifyFailure(error)
      }
    )

    onMounted(() => {
      dashboardStore.loadDashboardData()
      configStore.loadSchedule()
      mainStore.resetItemCount()
    })

    return {
      coreBuildDate,
      coreGitInfo,
      dashboard_data,
      buildDate,
      gitInfo,
      schedule_length,
      d
    }
  }
}
</script>
