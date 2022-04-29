<template>
  <ViewLayout>
    <template v-slot:panel> </template>
    <template v-slot:content>
      <v-row dense class="d-flex align-stretch">
        <adaptive-cardsize
          v-for="(topic, position) in topics"
          :key="position"
          :topic="topic"
          :position="position"
        ></adaptive-cardsize>
      </v-row>

      <v-row no-gutters>
        <v-col cols="6" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="white"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
                <wordcloud
                  :data="tag_cloud"
                  nameKey="word"
                  valueKey="word_quantity"
                  :color="myColors"
                  :showTooltip="false"
                  :rotate="myRotate"
                  :fontSize="fontSize"
                  :wordClick="wordClickHandler"
                >
                </wordcloud>
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Assess</div>
                <div class="subheading grey--text">
                  Tagcloud for latest collected news items.
                </div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2"> mdi-email-multiple </v-icon>
                <span class="caption grey--text"
                  >There are
                  <strong>{{ getData.total_news_items }}</strong> total Assess
                  items.</span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="6" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-card-text class="pt-0">
                <div class="title mb-2">Publish</div>
                <!--<div class="subheading grey&#45;&#45;text">Number of pending analyses per hour</div>-->
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="orange">
                  mdi-email-check-outline
                </v-icon>
                <span class="caption grey--text"
                  >There are <b>{{ getData.total_products }}</b> products ready
                  for publications.</span
                >
                <v-divider inset></v-divider>
              </v-card-text>
            </v-card>
          </template>
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col cols="4" class="pa-2 mb-4">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Analyze</div>
                <div class="subheading grey--text">Status of report items</div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2"> mdi-account </v-icon>
                <span class="caption grey--text"
                  >There are
                  <b>{{ getData.report_items_completed }}</b> completed
                  analyses.</span
                >
                <v-divider inset></v-divider>
                <v-icon class="mr-2" color="grey">
                  mdi-account-question-outline
                </v-icon>
                <span class="caption grey--text"
                  >There are
                  <b>{{ getData.report_items_in_progress }}</b> pending
                  analyses.</span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="4" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Collect</div>
                <div class="subheading grey--text">
                  Collectors activity status
                </div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="green">
                  mdi-lightbulb-off-outline
                </v-icon>
                <span class="caption grey--text"
                  >Collectors are pending at the moment.</span
                >
                <v-divider inset></v-divider>

                <v-icon class="mr-2"> mdi-clock-check-outline </v-icon>
                <span class="caption grey--text"
                  >Last successful run ended at
                  <b>{{ getData.latest_collected }}</b></span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="4" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Database</div>
                <div class="subheading grey--text">Number of live items</div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="blue"> mdi-database </v-icon>
                <span class="caption grey--text"
                  >There are <b>{{ getData.total_database_items }}</b> live
                  items.</span
                >
                <v-divider inset></v-divider>

                <v-icon class="mr-2"> mdi-database-check </v-icon>
                <span class="caption grey--text"
                  >There are <b>0</b> archived items.</span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
      </v-row>
    </template>
  </ViewLayout>
</template>

<script>
import wordcloud from 'vue-wordcloud'
import ViewLayout from '../../components/layouts/ViewLayout'
import AdaptiveCardsize from '@/components/layouts/AdaptiveCardsize'

export default {
  name: 'DashboardView',
  components: {
    wordcloud,
    ViewLayout,
    AdaptiveCardsize
  },
  computed: {
    getData () {
      return this.$store.getters.getDashboardData
    }
  },
  data: () => ({
    myColors: ['#1f77b4', '#629fc9', '#94bedb', '#c9e0ef'],
    myRotate: { from: 0, to: 0, numOfOrientation: 0 },
    fontSize: [14, 40],
    tag_cloud: [],
    labels: ['12am', '3am', '6am', '9am', '12pm', '3pm', '6pm', '9pm'],
    value: [200, 675, 410, 390, 310, 460, 250, 240],
    topics: [
      {
        title: 'Ukraine',
        tags: [
          { label: 'State', color: Math.floor(Math.random() * 20) },
          { label: 'Cyberwar', color: Math.floor(Math.random() * 20) },
          { label: 'Threat', color: Math.floor(Math.random() * 20) },
          { label: 'DDoS', color: Math.floor(Math.random() * 20) }
        ],
        ai: true,
        hot: true,
        pinned: true,
        last_activity: '15th March 2022',
        summary:
          'Cyber conflicts are fought in the shadous. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title: 'Log4J',
        tags: [
          { label: 'Vulnerability', color: Math.floor(Math.random() * 20) },
          { label: 'Java', color: Math.floor(Math.random() * 20) },
          { label: 'CVE', color: Math.floor(Math.random() * 20) }
        ],
        ai: false,
        hot: false,
        pinned: true,
        last_activity: '10th Jannuary 2022',
        summary:
          'Log4Shell (CVE-2021-44228) was a zer-day velnerability in Log4j. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title:
          'Siemens SIMATIC, this is a long title a very long title actually, maybe over 2 lines',
        ai: true,
        hot: false,
        pinned: false,
        tags: [
          { label: 'OT/CPS', color: Math.floor(Math.random() * 20) },
          { label: 'Siemens', color: Math.floor(Math.random() * 20) },
          {
            label: 'Information Disclosure',
            color: Math.floor(Math.random() * 20)
          }
        ],
        last_activity: '1st December 2021',
        summary:
          'The affected component stores the credentials of a local system account. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyamthe credentials of a local system account. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title: 'Ukraine',
        tags: [
          { label: 'State', color: Math.floor(Math.random() * 20) },
          { label: 'Cyberwar', color: Math.floor(Math.random() * 20) },
          { label: 'Threat', color: Math.floor(Math.random() * 20) },
          { label: 'DDoS', color: Math.floor(Math.random() * 20) }
        ],
        ai: true,
        hot: true,
        pinned: false,
        last_activity: '15th March 2022',
        summary:
          'Cyber conflicts are fought in the shadous. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title: 'Log4J',
        tags: [
          { label: 'Vulnerability', color: Math.floor(Math.random() * 20) },
          { label: 'Java', color: Math.floor(Math.random() * 20) },
          { label: 'CVE', color: Math.floor(Math.random() * 20) }
        ],
        ai: false,
        hot: false,
        pinned: false,
        last_activity: '10th Jannuary 2022',
        summary:
          'Log4Shell (CVE-2021-44228) was a zer-day velnerability in Log4j. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title:
          'Siemens SIMATIC, this is a long title a very long title actually, maybe over 2 lines',
        ai: true,
        hot: false,
        pinned: false,
        tags: [
          { label: 'OT/CPS', color: Math.floor(Math.random() * 20) },
          { label: 'Siemens', color: Math.floor(Math.random() * 20) },
          {
            label: 'Information Disclosure',
            color: Math.floor(Math.random() * 20)
          }
        ],
        last_activity: '1st December 2021',
        summary:
          'The affected component stores the credentials of a local system account. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyamthe credentials of a local system account. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title: 'Ukraine',
        tags: [
          { label: 'State', color: Math.floor(Math.random() * 20) },
          { label: 'Cyberwar', color: Math.floor(Math.random() * 20) },
          { label: 'Threat', color: Math.floor(Math.random() * 20) },
          { label: 'DDoS', color: Math.floor(Math.random() * 20) }
        ],
        ai: true,
        hot: true,
        pinned: false,
        last_activity: '15th March 2022',
        summary:
          'Cyber conflicts are fought in the shadous. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title: 'Log4J',
        tags: [
          { label: 'Vulnerability', color: Math.floor(Math.random() * 20) },
          { label: 'Java', color: Math.floor(Math.random() * 20) },
          { label: 'CVE', color: Math.floor(Math.random() * 20) }
        ],
        ai: false,
        hot: false,
        pinned: false,
        last_activity: '10th Jannuary 2022',
        summary:
          'Log4Shell (CVE-2021-44228) was a zer-day velnerability in Log4j. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title:
          'Siemens SIMATIC, this is a long title a very long title actually, maybe over 2 lines',
        ai: true,
        hot: false,
        pinned: false,
        tags: [
          { label: 'OT/CPS', color: Math.floor(Math.random() * 20) },
          { label: 'Siemens', color: Math.floor(Math.random() * 20) },
          {
            label: 'Information Disclosure',
            color: Math.floor(Math.random() * 20)
          }
        ],
        last_activity: '1st December 2021',
        summary:
          'The affected component stores the credentials of a local system account. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyamthe credentials of a local system account. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title: 'Ukraine',
        tags: [
          { label: 'State', color: Math.floor(Math.random() * 20) },
          { label: 'Cyberwar', color: Math.floor(Math.random() * 20) },
          { label: 'Threat', color: Math.floor(Math.random() * 20) },
          { label: 'DDoS', color: Math.floor(Math.random() * 20) }
        ],
        ai: true,
        hot: true,
        pinned: false,
        last_activity: '15th March 2022',
        summary:
          'Cyber conflicts are fought in the shadous. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title: 'Log4J',
        tags: [
          { label: 'Vulnerability', color: Math.floor(Math.random() * 20) },
          { label: 'Java', color: Math.floor(Math.random() * 20) },
          { label: 'CVE', color: Math.floor(Math.random() * 20) }
        ],
        ai: false,
        hot: false,
        pinned: false,
        last_activity: '10th Jannuary 2022',
        summary:
          'Log4Shell (CVE-2021-44228) was a zer-day velnerability in Log4j. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      },
      {
        title:
          'Siemens SIMATIC, this is a long title a very long title actually, maybe over 2 lines',
        ai: true,
        hot: false,
        pinned: false,
        tags: [
          { label: 'OT/CPS', color: Math.floor(Math.random() * 20) },
          { label: 'Siemens', color: Math.floor(Math.random() * 20) },
          {
            label: 'Information Disclosure',
            color: Math.floor(Math.random() * 20)
          }
        ],
        last_activity: '1st December 2021',
        summary:
          'The affected component stores the credentials of a local system account. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyamthe credentials of a local system account. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam',
        items: { total: 92, new: 35 },
        comments: { total: 92, new: 35 },
        votes: { up: 92, down: 35 }
      }
    ]
  }),
  methods: {
    wordClickHandler (name, value, vm) {
      window.console.log('wordClickHandler', name, value, vm)
    },

    refreshTagCloud () {
      this.$store.dispatch('getAllDashboardData').then(() => {
        this.tag_cloud = this.$store.getters.getDashboardData.tag_cloud
      })
    },
    stringToColor (string) {
      let hash = 0
      for (let i = 0; i < string.length; i++) {
        hash += string.charCodeAt(i)
      }
      return `#${Math.floor(parseFloat('0.' + hash) * 16777215).toString(16)}`
    }
  },
  mounted () {
    this.refreshTagCloud()

    setInterval(
      function () {
        this.refreshTagCloud()
      }.bind(this),
      600000
    )
  }
}
</script>
