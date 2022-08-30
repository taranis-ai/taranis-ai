<template>
  <v-container v-bind="UI.CARD.CONTAINER" data-type="item">
    <v-row>
      <v-col :class="UI.CLASS.card_offset">
          <v-card @click.stop="cardItemToolbar"
                  :color="selectedColor"
          >
            <!--CONTENT-->
            <v-layout v-bind="UI.CARD.LAYOUT" :class="'status ' + cardStatus">
              <v-row v-bind="UI.CARD.ROW.CONTENT">
                <!--COLLECTED, PUBLISHED, SOURCE-->
                <v-col v-bind="UI.CARD.COL.INFO">
                  <div>
                    {{ $t('card_item.collected') }}: <strong>{{ news_item.news_item_data.collected }}</strong>
                  </div>
                </v-col>
                <v-col v-bind="UI.CARD.COL.INFO">
                  <div align="center">
                    {{ $t('card_item.published') }}:
                    <strong>{{ news_item.news_item_data.published }}</strong>
                  </div>
                </v-col>
                <v-col v-bind="UI.CARD.COL.INFO">
                  <div align="right">
                    {{ $t('card_item.source') }}:
                    <strong>{{ news_item.news_item_data.source }}</strong>
                  </div>
                </v-col>
              </v-row>
              <!--TITLE-->
              <v-row>
                <v-col>
                  <v-card-title v-bind="UI.CARD.COL.TITLE">
                    <div v-html="news_item.news_item_data.title"></div>
                  </v-card-title>
                  <!--REVIEW-->
                  <v-card-text v-bind="UI.CARD.COL.REVIEW">
                    <div v-html="news_item.news_item_data.review"></div>
                  </v-card-text>
                </v-col>
              </v-row>
            </v-layout>
          </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { groupAction, voteNewsItem, readNewsItem, importantNewsItem, deleteNewsItem } from '@/api/assess'

import AuthMixin from '@/services/auth/auth_mixin'
import Permissions from '@/services/auth/permissions'

export default {
  name: 'CardAssessItem',
  props: {
    news_item: Object,
    analyze_selector: Boolean
  },
  mixins: [AuthMixin],
  data: () => ({
    toolbar: false,
    selected: false
  }),
  computed: {
    multiSelectActive () {
      return this.$store.getters.getMultiSelect
    },
    selectedColor () {
      if (this.selected === true) {
        return 'orange lighten-4'
      } else {
        return ''
      }
    },
    cardStatus () {
      if (this.news_item.important) {
        return 'important'
      } else if (this.news_item.read) {
        return 'read'
      } else {
        return 'new'
      }
    }
  },
  methods: {
    itemClicked (data) {
      if (this.checkPermission(Permissions.ASSESS_ACCESS) && this.news_item.access === true) {
        this.$emit('show-item-detail', data)
        this.stateChange()
      }
    },
    selectionChanged () {
      if (this.selected === true) {
        this.$store.dispatch('select', { type: 'ITEM', id: this.news_item.id, item: this.news_item })
      } else {
        this.$store.dispatch('deselect', { type: 'ITEM', id: this.news_item.id, item: this.news_item })
      }
    },
    stateChange () {
      this.$root.$emit('change-state', 'SHOW_ITEM')
      this.$root.$emit('check-focus', this.$el.dataset.id)
      this.$root.$emit('update-pos', parseInt(this.$el.dataset.id))
    },
    getGroupId () {
      if (window.location.pathname.includes('/group/')) {
        const i = window.location.pathname.indexOf('/group/')
        const len = window.location.pathname.length
        return window.location.pathname.substring(i + 7, len)
      } else {
        return null
      }
    },
    cardItemToolbar (action) {
      switch (action) {
        case 'like':
          voteNewsItem(this.getGroupId(), this.news_item.id, 1).then(() => {
          })
          break

        case 'unlike':
          voteNewsItem(this.getGroupId(), this.news_item.id, -1).then(() => {
          })
          break

        case 'link':
          break

        case 'important':
          importantNewsItem(this.getGroupId(), this.news_item.id).then(() => {
          })
          break

        case 'read':
          readNewsItem(this.getGroupId(), this.news_item.id).then(() => {
          })
          break

        case 'delete':
          deleteNewsItem(this.getGroupId(), this.news_item.id).then(() => {
          }).catch((error) => {
            this.$root.$emit('notification',
              {
                type: 'error',
                loc: 'error.' + error.response.data
              }
            )
          })
          break

        case 'ungroup':
          groupAction({
            group: this.getGroupId(),
            action: 'UNGROUP',
            items: [{ type: 'ITEM', id: this.news_item.id }]
          }).then(() => {
          }).catch((error) => {
            this.$root.$emit('notification',
              {
                type: 'error',
                loc: 'error.' + error.response.data
              }
            )
          })
          break

        default:
          this.toolbar = false
          this.itemClicked(this.news_item)
          break
      }
    },

    buttonStatus: function (active) {
      if (active) {
        return 'info'
      } else {
        return 'accent'
      }
    },
    multiSelectOff () {
      this.selected = false
    },
    setFocus (id) {
      if (this.$el.dataset.id === id) {
        this.toolbar = true
        this.$el.querySelector('.card .layout').classList.add('focus')
      } else {
        this.toolbar = false
        this.$el.querySelector('.card .layout').classList.remove('focus')
      }
    }
  },
  mounted () {
    this.$root.$on('multi-select-off', this.multiSelectOff)

    this.$root.$on('check-focus', (id) => {
      this.setFocus(id)
    })
  },
  beforeDestroy () {
    this.$root.$off('multi-select-off', this.multiSelectOff)
  }
}
</script>
