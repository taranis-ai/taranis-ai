<template>
  <v-card>
    <v-toolbar dark color="secondary">
      <v-toolbar-title>{{ story.title }}</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn icon :title="$t('assess.tooltip.delete_item')">
        <v-icon color="red">mdi-delete</v-icon>
      </v-btn>
    </v-toolbar>

    <v-container fluid>
      <v-row class="text-center">
        <v-col>
          <span class="overline font-weight-bold">
            {{ $t('assess.created') }}
          </span>
          <br />
          <span class="caption">
            {{ $d(new Date(story.created), 'long') }}
          </span>
        </v-col>
        <v-col>
          <span class="overline font-weight-bold"> NewsItem ID </span>
          <br />
          <span class="caption">
            {{ story.id }}
          </span>
        </v-col>
      </v-row>
      <v-row align="center" justify="center" class="mt-5 mb-5">
        <tag-list
          key="tags"
          :limit="getTags.length"
          :truncate="false"
          :tags="getTags"
        />
      </v-row>
      <v-row>
        <span class="display-1 font-weight-light py-4">
          {{ story.title }}
        </span>
      </v-row>
      <v-row class="py-4">
        <span>{{ getDescription }}</span>
      </v-row>
    </v-container>
  </v-card>
</template>

<script>
import TagList from '@/components/common/tags/TagList'

export default {
  name: 'StoryDetail',
  components: {
    TagList
  },
  emits: ['view'],
  props: {
    story: {}
  },
  data: () => ({}),
  computed: {
    getTags() {
      return this.story.tags.map((tag) => tag.name)
    },
    getDescription() {
      return this.story.summary || this.story.description
    }
  },
  mounted() {
    console.log(this.story)
  },
  methods: {}
}
</script>
