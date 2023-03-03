<template>
  <v-container fluid>
    <v-row no-gutters>
      <dash-board-card linkTo="/assess" linkText="Assess" cols="6">
        <template v-slot:content>
          <v-icon class="mr-2"> mdi-email-multiple </v-icon>
          <span class="caption">
            There are
            <strong>{{ dashboardData.total_news_items }}</strong> total Assess
            items.
          </span>
        </template>
      </dash-board-card>
      <dash-board-card linkTo="/publish" linkText="Publish" cols="6">
        <template v-slot:content>
          <v-icon class="mr-2" color="orange"> mdi-email-check-outline </v-icon>
          <span class="caption">
            There are <b>{{ dashboardData.total_products }}</b> products ready
            for publications.
          </span>
        </template>
      </dash-board-card>
    </v-row>
    <v-row no-gutters>
      <dash-board-card linkTo="/analyze" linkText="Analyze">
        <template v-slot:content>
          <v-icon class="mr-2"> mdi-account </v-icon>
          <span class="caption">
            There are <b>{{ dashboardData.report_items_completed }}</b>
            completed analyses.
          </span>
          <v-divider inset></v-divider>
          <v-icon class="mr-2" color="grey">
            mdi-account-question-outline
          </v-icon>
          <span class="caption">
            There are <b>{{ dashboardData.report_items_in_progress }}</b>
            pending analyses.
          </span>
        </template>
      </dash-board-card>
      <dash-board-card linkTo="/config/nodes" linkText="Nodes">
        <template v-slot:content>
          <v-icon class="mr-2" color="green">
            mdi-lightbulb-off-outline
          </v-icon>
          <span class="caption">Collectors are pending</span>
          <v-divider inset></v-divider>

          <v-icon class="mr-2"> mdi-clock-check-outline </v-icon>
          <span class="caption"
            >Last successful run ended at
            <b>{{ dashboardData.latest_collected }}</b></span
          >
        </template>
      </dash-board-card>
      <dash-board-card linkTo="#" linkText="Database">
        <template v-slot:content>
          <v-icon class="mr-2" color="blue"> mdi-database </v-icon>
          <span class="caption"
            >There are <b>{{ dashboardData.total_database_items }}</b> live
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
import { mapGetters, mapActions } from 'vuex'
import DashBoardCard from '@/components/common/DashBoardCard'

export default {
  name: 'DashBoardConfig',
  components: { DashBoardCard },
  data: () => ({
    dashboardData: {}
  }),
  computed: {
    totalItems() {
      return this.getItemCount().total
    }
  },
  methods: {
    ...mapActions('dashboard', ['loadDashboardData']),
    ...mapGetters('dashboard', ['getDashboardData']),
    ...mapGetters(['getItemCount'])
  },
  mounted() {
    this.loadDashboardData().then(() => {
      this.dashboardData = this.getDashboardData()
    })
  }
}
</script>
