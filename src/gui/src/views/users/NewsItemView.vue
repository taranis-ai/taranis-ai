<template>
  <v-container fluid style="min-height: 100vh">
    <v-card>
      <v-toolbar dark color="secondary">
        <v-btn icon dark @click.native="close">
          <v-icon>close</v-icon>
        </v-btn>
        <v-toolbar-title>{{ news_item.news_item_data.title }}</v-toolbar-title>
        <v-spacer></v-spacer>
      </v-toolbar>
      <v-row justify="center" class="px-4 py-4">
        <v-row justify="center" class="subtitle-2 info--text pt-4 ma-0">
          <v-flex>
            <v-row class="text-center">
              <v-col>
                <span class="overline font-weight-bold">
                  {{ $t('assess.collected') }}
                </span>
                <br />
                <span class="caption">
                  {{ $d(new Date(news_item.news_item_data.collected), 'long') }}
                </span>
              </v-col>
              <v-col>
                <span class="overline font-weight-bold">
                  {{ $t('assess.published') }}
                </span>
                <br />
                <span class="caption">
                  {{ $d(new Date(news_item.news_item_data.published), 'long') }}
                </span>
              </v-col>
              <v-col>
                <span class="overline font-weight-bold">
                  {{ $t('assess.source') }} </span
                ><br />
                <span class="caption">
                  {{ news_item.news_item_data.source }}
                </span>
              </v-col>
              <v-col>
                <span class="overline font-weight-bold">
                  {{ $t('assess.author') }}
                </span>
                <br />
                <span class="caption">
                  {{ news_item.news_item_data.author }}
                </span>
              </v-col>
              <v-col>
                <span class="overline font-weight-bold"> ID </span>
                <br />
                <span class="caption">
                  {{ news_item.id }}
                </span>
              </v-col>
            </v-row>
          </v-flex>
        </v-row>
        <hr style="width: calc(100%); border: 0px" />
        <v-row class="headline">
          <span class="display-1 font-weight-light py-4">
            {{ news_item.news_item_data.title }}
          </span>
        </v-row>
        <v-row class="py-4">
          <span>{{ getDescription }}</span>
        </v-row>

        <!-- LINKS -->
        <v-container fluid>
          <v-row>
            <a
              :href="news_item.news_item_data.link"
              target="_blank"
              rel="noreferrer"
            >
              <span>{{ news_item.news_item_data.link }}</span>
            </a>
          </v-row>
        </v-container>
      </v-row>
    </v-card>
  </v-container>
</template>

<script>
import { getNewsItem } from '@/api/assess'

export default {
  name: 'NewsItemView',
  data: () => ({
    news_item: {}
  }),
  computed: {
    getDescription() {
      return (
        this.news_item.news_item_data.content ||
        this.news_item.news_item_data.review
      )
    }
  },
  async created() {
    this.news_item = await this.loadNewsItem()
    console.debug(this.news_item)
  },
  methods: {
    async loadNewsItem() {
      if (this.$route.params.id) {
        return await getNewsItem(this.$route.params.id).then((response) => {
          return response.data
        })
      }
    }
  }
}
</script>
