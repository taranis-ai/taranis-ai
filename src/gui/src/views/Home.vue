<template>
  <v-container fluid>
    <v-row no-gutters>
      <v-col cols="4" class="pa-2 mb-8">
          <v-card class="mt-4 mx-auto" max-width="100%">
            <v-card-text class="pt-0">
              <router-link to="/assess" class="title">Assess</router-link>
              <div class="subheading">news items</div>
              <v-divider class="my-2"></v-divider>
              <v-icon class="mr-2"> mdi-email-multiple </v-icon>
              <span class="caption"
                >There are
                <strong>{{ dashboardData.total_news_items }}</strong> total
                Assess items.</span
              >
            </v-card-text>
          </v-card>
      </v-col>
      <v-col cols="4" class="pa-2 mb-4">
          <v-card class="mt-4 mx-auto" max-width="100%">
            <v-card-text class="pt-0">
              <router-link to="/analyze" class="title">Analyze</router-link>
              <div class="subheading">report items</div>
              <v-divider class="my-2"></v-divider>
              <v-icon class="mr-2"> mdi-account </v-icon>
              <span class="caption"
                >There are
                <b>{{ dashboardData.report_items_completed }}</b> completed
                analyses.</span
              >
              <v-divider inset></v-divider>
              <v-icon class="mr-2" color="grey">
                mdi-account-question-outline
              </v-icon>
              <span class="caption"
                >There are
                <b>{{ dashboardData.report_items_in_progress }}</b> pending
                analyses.</span
              >
            </v-card-text>
          </v-card>
      </v-col>
      <v-col cols="4" class="pa-2 mb-8">
          <v-card class="mt-4 mx-auto" max-width="100%">
            <v-card-text class="pt-0">
              <router-link to="/publish" class="title">Publish</router-link>
              <div class="subheading">products</div>
              <v-divider class="my-2"></v-divider>
              <v-icon class="mr-2" color="orange">
                mdi-email-check-outline
              </v-icon>
              <span class="caption"
                >There are <b>{{ dashboardData.total_products }}</b> products
                ready for publications.</span
              >
              <v-divider inset></v-divider>
            </v-card-text>
          </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'

export default {
  name: 'Home',
  components: {},
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
