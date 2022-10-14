<template>
  <ViewLayout>
    <template v-slot:content>
      <v-row no-gutters>
        <v-col cols="6" class="pa-2 mb-8">
          <template>
            <v-card
              class="mt-4 mx-auto"
              max-width="100%"
            >
            <v-card-text class="pt-0">
              <div class="title mb-2">Assess</div>
              <v-divider class="my-2"></v-divider>
              <v-icon class="mr-2">
                mdi-email-multiple
              </v-icon>
              <span
                class="caption grey--text">There are <strong>{{ getData.total_news_items }}</strong> total Assess items.</span>

              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="6" class="pa-2 mb-8">
          <template>
            <v-card
              class="mt-4 mx-auto"
              max-width="100%"
            >

              <v-card-text class="pt-0">
                <div class="title mb-2">Publish</div>
                <!--<div class="subheading grey&#45;&#45;text">Number of pending analyses per hour</div>-->
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="orange">
                  mdi-email-check-outline
                </v-icon>
                <span class="caption grey--text">There are <b>{{ getData.total_products }}</b> products ready for publications.</span>
                <v-divider inset></v-divider>

              </v-card-text>
            </v-card>
          </template>
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col cols="4" class="pa-2 mb-4">
          <template>
            <v-card
              class="mt-4 mx-auto"
              max-width="100%"
            >
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
              </v-sheet>

              <v-card-text class="pt-0">
                <!--<v-btn icon class="align-self-start next" size="28">
                  <v-icon>mdi-arrow-right-thick</v-icon>
                </v-btn>-->
                <div class="title mb-2">Analyze</div>
                <div class="subheading grey--text">Status of report items</div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2">
                  mdi-account
                </v-icon>
                <span class="caption grey--text">There are <b>{{ getData.report_items_completed }}</b> completed analyses.</span>
                <v-divider inset></v-divider>
                <v-icon class="mr-2" color="grey">
                  mdi-account-question-outline
                </v-icon>
                <span class="caption grey--text">There are <b>{{ getData.report_items_in_progress }}</b> pending analyses.</span>
              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="4" class="pa-2 mb-8">
          <template>
            <v-card
              class="mt-4 mx-auto"
              max-width="100%"
            >
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              ></v-sheet>

              <v-card-text class="pt-0">
                <!--<v-btn icon class="align-self-start next" size="28">
                  <v-icon>mdi-arrow-right-thick</v-icon>
                </v-btn>-->
                <div class="title mb-2">Collect</div>
                <div class="subheading grey--text">Collectors activity status</div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="green">
                  mdi-lightbulb-off-outline
                </v-icon>
                <span class="caption grey--text ">Collectors are pending at the moment.</span>
                <v-divider inset></v-divider>

                <v-icon class="mr-2">
                  mdi-clock-check-outline
                </v-icon>
                <span
                  class="caption grey--text ">Last successful run ended at <b>{{
                    getData.latest_collected
                  }}</b></span>

              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="4" class="pa-2 mb-8">
          <template>
            <v-card
              class="mt-4 mx-auto"
              max-width="100%"
            >
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              ></v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Database</div>
                <div class="subheading grey--text">Number of live items</div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="blue">
                  mdi-database
                </v-icon>
                <span class="caption grey--text">There are <b>{{ getData.total_database_items }}</b> live items.</span>
                <v-divider inset></v-divider>

                <v-icon class="mr-2">
                  mdi-database-check
                </v-icon>
                <span class="caption grey--text">There are <b>0</b> archived items.</span>

              </v-card-text>
            </v-card>
          </template>
        </v-col>
      </v-row>
    </template>
  </ViewLayout>
</template>

<script>
import ViewLayout from '../../components/layouts/ViewLayout'
import { mapGetters, mapActions } from 'vuex'

export default {
  name: 'Config',
  components: {
    ViewLayout
  },
  computed: {
    getData() {
      return this.getDashboardData()
    }
  },
  data: () => ({

  }),
  methods: {
    ...mapActions('dashboard', ['getAllDashboardData']),
    ...mapGetters('dashboard', ['getDashboardData'])
  },
  mounted() {
    // this.refreshTagCloud()
  }
}
</script>
