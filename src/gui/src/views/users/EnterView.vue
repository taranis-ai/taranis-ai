<template>
  <v-form
    id="form"
    ref="form"
    style="width: 100%; padding: 8px"
    @submit.prevent="add"
  >
    <v-card>
      <v-card-text>
        <v-text-field
          v-model="news_item.title"
          v-validate="'required'"
          :label="$t('enter.title')"
          name="title"
          type="text"
          data-vv-name="title"
          :error-messages="errors.collect('title')"
        ></v-text-field>

        <v-textarea
          v-model="news_item.review"
          :label="$t('enter.review')"
          name="review"
        ></v-textarea>

        <v-text-field
          v-model="news_item.source"
          :label="$t('enter.source')"
          name="source"
          type="text"
        ></v-text-field>

        <v-text-field
          v-model="news_item.link"
          :label="$t('enter.link')"
          name="link"
          type="text"
        ></v-text-field>

        <quill-editor
          v-model:content="editorData"
          placeholder="insert text here ..."
        />
      </v-card-text>
    </v-card>
    <v-spacer class="pt-2"></v-spacer>
    <v-btn color="primary" @click="add()">{{ $t('enter.create') }}</v-btn>
  </v-form>
</template>

<script>
import { QuillEditor } from '@vueup/vue-quill'
import { addNewsItem } from '@/api/assess'
import { notifySuccess } from '@/utils/helpers'
import { mapState } from 'pinia'
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'EnterView',
  components: {
    QuillEditor
  },
  data: () => ({
    show_error: false,
    show_validation_error: false,

    editorData: '',

    news_item: {
      id: '',
      title: '',
      review: '',
      content: '',
      link: '',
      source: '',
      author: '',
      language: '',
      hash: '',
      osint_source_id: '',
      published: '',
      collected: '',
      attributes: []
    }
  }),
  computed: {
    ...mapState(useMainStore, ['user'])
  },
  methods: {
    add() {
      this.$validator.validateAll().then(() => {
        if (!this.$validator.errors.any()) {
          this.news_item.content = this.editorData

          const i = window.location.pathname.indexOf('/source/')
          const len = window.location.pathname.length
          this.news_item.osint_source_id = window.location.pathname.substring(
            i + 8,
            len
          )

          this.news_item.author = this.user.name
          const d = new Date()
          this.news_item.collected =
            this.appendLeadingZeroes(d.getDate()) +
            '.' +
            this.appendLeadingZeroes(d.getMonth() + 1) +
            '.' +
            d.getFullYear() +
            ' - ' +
            this.appendLeadingZeroes(d.getHours()) +
            ':' +
            this.appendLeadingZeroes(d.getMinutes())
          this.news_item.published = this.news_item.collected

          addNewsItem(this.news_item)
            .then(() => {
              this.news_item.id = ''
              this.news_item.title = ''
              this.news_item.review = ''
              this.news_item.content = ''
              this.news_item.link = ''
              this.news_item.source = ''
              this.news_item.author = ''
              this.news_item.language = ''
              this.news_item.hash = ''
              this.news_item.osint_source_id = ''
              this.news_item.published = ''
              this.news_item.collected = ''
              this.news_item.attributes = []

              this.$validator.reset()

              this.editorData = '<p></p>'

              notifySuccess('enter.successful')
            })
            .catch(() => {
              this.show_error = true
            })
        } else {
          this.show_validation_error = true
        }
      })
    },

    appendLeadingZeroes(n) {
      if (n <= 9) {
        return '0' + n
      }
      return n
    }
  }
}
</script>
