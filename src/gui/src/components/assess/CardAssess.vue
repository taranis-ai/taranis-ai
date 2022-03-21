<template>
  <v-container v-bind="UI.CARD.CONTAINER" :data-type="this.cardType" :data-open="opened" :data-set="data_set">
    <v-row>
      <v-col v-if="multiSelectActive" :style="UI.STYLE.card_selector_zone">
          <v-row justify="center" align="center">
              <v-checkbox v-if="!preselected" v-model="selected" @change="selectionChanged"/>
          </v-row>
      </v-col>
      <v-col :class="UI.CLASS.card_offset">
        <v-hover v-slot="{hover}">
          <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2"
                  @click.stop="cardItemToolbar"
                  @mouseenter.native="toolbar=true"
                  @mouseleave.native="toolbar=cardFocus"
                  :color="selectedColor"
          >
            <!--CONTENT-->
            <v-layout v-bind="UI.CARD.LAYOUT" :class="'status ' + cardStatus">
              <v-row>
                <v-col cols="8">
                <!--TITLE-->
                <v-card-title v-bind="UI.CARD.COL.TITLE">
                  <div v-html="card_title"></div>
                </v-card-title>
                <!--REVIEW-->
                <v-card-text v-bind="UI.CARD.COL.REVIEW">
                  <div class="compact" v-html="card_description"></div>
                </v-card-text>
                </v-col>
                <!--FOOTER-->
                <v-col cols="4">
                  <v-card-actions>
                    <v-row class="d-flex">
                      <span v-if="!singleAggregate" class="subtitle-2">
                        {{ $t('card_item.aggregated_items') }}: {{ card.news_items.length }}
                      </span>
                      <v-btn v-if="card.in_reports_count > 0" depressed x-small color="orange lighten-2">
                          {{ $t('card_item.in_analyze') }}
                      </v-btn>
                        <v-btn v-if="!singleAggregate && canModify" icon
                                @click.stop="cardItemToolbar('ungroup')"
                                data-btn="ungroup"
                                :title="$t('assess.tooltip.ungroup_news_item')">
                            <v-icon color="accent">mdi-ungroup</v-icon>
                        </v-btn>
                        <v-btn v-if="canCreateReport" icon @click.stop="cardItemToolbar('new')" :title="$t('assess.tooltip.analyze_item')" data-btn="new">
                            <v-icon color="accent">mdi-file-outline</v-icon>
                        </v-btn>
                        <div v-if="canModify">
                          <v-btn icon @click.stop="cardItemToolbar('read')" data-btn="read" :title="$t('assess.tooltip.read_item')">
                              <v-icon :color="buttonStatus(card.read)">mdi-eye</v-icon>
                          </v-btn>
                          <v-btn icon @click.stop="cardItemToolbar('important')" :title="$t('assess.tooltip.important_item')" data-btn="important">
                              <v-icon :color="buttonStatus(card.important)">mdi-star</v-icon>
                          </v-btn>

                          <v-btn icon @click.stop="cardItemToolbar('like')" data-btn="like" :title="$t('assess.tooltip.like_item')">
                              <v-badge v-if="card.likes" bordered color="green" :content="card.likes" overlap left>
                                <v-icon :color="buttonStatus(card.me_like)">mdi-thumb-up</v-icon>
                              </v-badge>
                              <v-icon v-else :color="buttonStatus(card.me_like)">mdi-thumb-up</v-icon>
                          </v-btn>
                          <v-btn icon @click.stop="cardItemToolbar('unlike')" :title="$t('assess.tooltip.dislike_item')" data-btn="unlike">
                              <v-badge v-if="card.dislikes" bordered color="red" :content="card.dislikes" overlap>
                                <v-icon :color="buttonStatus(card.me_dislike)">mdi-thumb-down</v-icon>
                              </v-badge>
                              <v-icon v-else :color="buttonStatus(card.me_dislike)">mdi-thumb-down</v-icon>
                          </v-btn>
                        </div>
                        <v-btn v-if="canDelete" icon @click.stop="cardItemToolbar('delete')"
                                :title="$t('assess.tooltip.delete_item')"
                                data-btn="delete">
                            <v-icon color="accent">{{ UI.ICON.DELETE }}</v-icon>
                        </v-btn>
                        <v-spacer />
                        <v-btn v-if="analyze_selector && analyze_can_modify" v-bind="UI.CARD.TOOLBAR.COMPACT" icon @click.stop="cardItemToolbar('remove')">
                          <v-icon color="accent">mdi-minus-circle-outline</v-icon>
                        </v-btn>
                    </v-row>
                  </v-card-actions>
                  <div v-if="singleAggregate">
                    <v-row>
                      {{ $t('card_item.collected') }}: <strong>{{ card.created }}</strong>
                    </v-row>
                    <v-row>
                        {{ $t('card_item.published') }}: <strong>{{ get_pub_date(news_items[0]) }}</strong>
                    </v-row>
                    <v-row>
                        {{ $t('card_item.source') }}:
                        <a target="_blank" rel="noreferer" @click.stop="" :title="itemLink" :href="itemLink">
                          {{ extract_domain(itemLink) }} <v-icon color="accent">mdi-open-in-app</v-icon>
                        </a>
                    </v-row>
                  </div>

                    <v-row class="d-flex">
                      <v-btn v-for="tag in getTags" :key="tag" rounded :color="stringToColor(tag)" dark x-small @click.stop="filterTags(tag)">
                        {{ tag }}
                      </v-btn>
                      <v-spacer />
                      <v-icon v-if="opened" left>mdi-arrow-down-drop-circle</v-icon>
                      <v-icon v-if="!opened" left>mdi-arrow-right-drop-circle</v-icon>
                    </v-row>
                </v-col>
              </v-row>
            </v-layout>
          </v-card>
        </v-hover>
      </v-col>
    </v-row>

    <div v-if="opened" dark class="ml-16 mb-8 grey lighten-4 rounded">
        <CardAssessItem v-for="news_item in news_items"
                        :key="news_item.id"
                        :news_item="news_item"
                        :analyze_selector="analyze_selector"
                        @show-item-detail="showItemDetail(news_item)"
        />
    </div>
  </v-container>
</template>

<script>
import CardAssessItem from '@/components/assess/CardAssessItem'
import {
  deleteNewsItemAggregate,
  groupAction,
  importantNewsItemAggregate,
  readNewsItemAggregate,
  voteNewsItemAggregate
} from '@/api/assess'

import AuthMixin from '@/services/auth/auth_mixin'
import Permissions from '@/services/auth/permissions'

export default {
  name: 'CardAssess',
  props: {
    card: Object,
    analyze_selector: Boolean,
    analyze_can_modify: Boolean,
    compact_mode: Boolean,
    preselected: Boolean,
    word_list_regex: String,
    aggregate_opened: Boolean,
    data_set: String,
    filter: Object
  },
  mixins: [AuthMixin],
  components: { CardAssessItem },
  data: () => ({
    toolbar: false,
    opened: false,
    selected: false,
    tag_filter: '',
    card_title: '',
    card_description: '',
    news_items: []
  }),
  filters: {
    truncate: function (data, length) {
      const reqdString = data.split('').slice(0, length).join('')
      return data.length > length ? reqdString + '...' : data
    }
  },
  computed: {
    canAccess () {
      return this.checkPermission(Permissions.ASSESS_ACCESS)
    },

    canModify () {
      return this.checkPermission(Permissions.ASSESS_UPDATE)
    },

    canDelete () {
      return this.checkPermission(Permissions.ASSESS_DELETE)
    },

    canCreateReport () {
      return this.checkPermission(Permissions.ANALYZE_CREATE)
    },

    multiSelectActive () {
      return this.$store.getters.getMultiSelect
    },
    selectedColor () {
      return ((this.selected || this.preselected) ? 'orange lighten-4' : '')
    },
    singleAggregate () {
      return this.card.news_items.length === 1
    },
    itemLink () {
      return (this.news_items.length === 1) ? this.news_items[0].news_item_data.link : ''
    },
    getTags () {
      return (this.news_items.length === 1) ? this.news_items[0].news_item_data.tags : ['']
    },
    cardType () {
      if (this.singleAggregate) {
        return 'single'
      } else {
        return 'aggregate'
      }
    },
    cardFocus () {
      return this.$el.querySelector('.card .layout').classList.contains('focus')
    },
    cardStatus () {
      if (this.card.important) {
        return 'important'
      } else if (this.card.read) {
        return 'read'
      } else {
        return 'new'
      }
    }
  },
  methods: {
    highlight (content) {
      if (this.word_list_regex) {
        return this.wordCheck(content)
      }
      try {
        content = this.removeHtml(content)
        if (this.filter.search === '' && this.tag_filter === '') {
          return content
        }

        let regex = this.filter.search
        if (regex === '') {
          regex = this.tag_filter
        } else {
          if (this.tag_filter !== '') {
            regex += '|' + this.tag_filter
          }
        }
        return this.highlightReplace(content, regex)
      } catch {
        return content
      }
    },
    stringToColor (string) {
      let hash = 0
      for (let i = 0; i < string.length; i++) {
        hash += string.charCodeAt(i)
      }
      return `#${Math.floor((parseFloat(`0.${hash}`)) * 16777215).toString(16)}`
    },
    highlightReplace (content, regex) {
      return content.replace(new RegExp(regex, 'gi'), match => {
        return `<mark>${match}</mark>`
      })
    },
    showItemDetail (data) {
      this.$emit('show-item-detail', data)

      this.stateChange('SHOW_ITEM')
    },
    openCard () {
      this.opened = !this.opened

      this.$emit('i', { id: this.card.id, opened: this.opened })
      this.$emit('card-items-reindex')
      this.$root.$emit('key-remap')
    },
    selectionChanged () {
      if (this.selected === true) {
        this.$store.dispatch('select', { type: 'AGGREGATE', id: this.card.id, item: this.card })
      } else {
        this.$store.dispatch('deselect', { type: 'AGGREGATE', id: this.card.id, item: this.card })
      }
    },
    filterTags (tag) {
      this.tag_filter = tag
      this.$emit('update-news-items-filter', { tag: tag })
    },
    itemClicked (data) {
      if (this.card.news_items.length === 1) {
        this.$emit('show-single-aggregate-detail', {
          data: data,
          isSelector: this.analyze_selector,
          id: this.$parent.selfID
        })
      } else {
        this.$emit('show-aggregate-detail', {
          data: data,
          isSelector: this.analyze_selector,
          id: this.$parent.selfID
        })
      }
      this.stateChange('SHOW_ITEM')
    },

    stateChange (_state) {
      this.$root.$emit('change-state', _state)
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
    get_pub_date (news_item) {
      if (news_item !== undefined) {
        if (news_item.news_item_data !== undefined) {
          if (news_item.news_item_data.published !== undefined) {
            return news_item.news_item_data.published
          }
        }
      }
    },
    cardItemToolbar (action) {
      switch (action) {
        case 'like':
          voteNewsItemAggregate(this.getGroupId(), this.card.id, 1).then(() => {
          })
          break

        case 'unlike':
          voteNewsItemAggregate(this.getGroupId(), this.card.id, -1).then(() => {
          })
          break

        case 'link':
          break

        case 'new':
          // window.console.debug("CLICK NEW");
          this.$root.$emit('new-report', [this.card])
          // this.stateChange('NEW_PRODUCT');
          // this.$root.$emit('mouse-click-analyze');
          break

        case 'remove':
          this.$emit('remove-item-from-selector', this.card)
          break

        case 'important':
          importantNewsItemAggregate(this.getGroupId(), this.card.id).then(() => {
          })
          break

        case 'read':
          readNewsItemAggregate(this.getGroupId(), this.card.id).then(() => {
          })
          break

        case 'delete':
          deleteNewsItemAggregate(this.getGroupId(), this.card.id).then(() => {
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
            items: [{ type: 'AGGREGATE', id: this.card.id }]
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
          this.openCard()
          // this.itemClicked(this.card);
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
    wordCheck (target) {
      const parse = new Array()
      const message = this.escapeHtml(target).split(' ')
      const word_list = new RegExp(this.word_list_regex, 'gi')

      for (let i = 0; i < message.length; i++) {
        const res = message[i].replace(word_list, function (x) {
          return "<span class='wordlist'>" + x + '</span>'
        })

        parse.push(res + ' ')
      }

      return parse.join('')
    },
    escapeHtml (text) {
      const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
      }

      return text.replace(/[&<>"']/g, function (m) {
        return map[m]
      })
    },
    removeHtml (html) {
      const div = document.createElement('div')
      div.innerHTML = html
      return div.textContent || div.innerText || ''
    },
    extract_domain (url) {
      try {
        const domain = (new URL(url))
        return domain.hostname
      } catch {
        return ''
      }
    },
    multiSelectOff () {
      this.selected = false
    },
    setFocus (id) {
      if (this.$el.dataset.id == id) {
        this.toolbar = true
        this.$el.querySelector('.card .layout').classList.add('focus')
      } else {
        this.toolbar = false
        this.$el.querySelector('.card .layout').classList.remove('focus')
      }
    }
  },
  created () {
    this.opened = this.aggregate_opened
  },
  mounted () {
    this.$root.$on('multi-select-off', this.multiSelectOff)

    this.$root.$on('check-focus', (id) => {
      this.setFocus(id)
    })
    this.card_title = this.highlight(this.card.title)
    this.card_description = this.highlight(this.card.description)
    for (const news_item of this.card.news_items) {
      news_item.news_item_data.title = this.highlight(news_item.news_item_data.title)
      news_item.news_item_data.review = this.highlight(news_item.news_item_data.review)
      this.news_items.push(news_item)
    }
  },
  beforeDestroy () {
    this.$root.$off('multi-select-off', this.multiSelectOff)
    this.$root.$off('check-focus')
  }
}
</script>
