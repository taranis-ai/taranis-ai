<template>
  <v-navigation-drawer
    v-if="filteredLinks.length > 0 && drawerVisible"
    clipped
    app
    color="cx-drawer-bg"
    class="sidebar"
    :width="width"
    style="max-height: 100% !important; height: calc(100vh - 48px) !important"
  >
    <v-layout class="navigation" fill-height justify-center>
      <v-list class="navigation-list pa-0">
        <v-list-item class="section-icon" dense>
          <v-list-item-title>
              <v-icon class="" color="white">{{icon}}</v-icon>
          </v-list-item-title>
        </v-list-item>
        <v-divider class="section-divider" color="white"></v-divider>

        <v-list-item class="px-1" v-for="link in filteredLinks" :key="link.id" router :to="link.route">
          <v-list-item-content class="py-2" v-if="!link.separator">
            <v-icon color="cx-drawer-text">{{ link.icon }}</v-icon>
            <v-list-item-title class="cx-drawer-text--text caption">{{ $t(link.title) }}</v-list-item-title>
          </v-list-item-content>
          <v-list-item-content class="separator py-0 blue-grey" v-else>
            <v-divider class="section-divider " color="white"></v-divider>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-layout>
  </v-navigation-drawer>
</template>

<script>
import AuthMixin from '@/services/auth/auth_mixin'
import { mapState } from 'vuex'

export default {
  name: 'Navigation',
  props: {
    titles: Array,
    links: Array,
    icon: String,
    filter: Boolean,
    width: {
      type: Number,
      default: 142
    }
  },
  mixins: [AuthMixin],
  data: () => ({}),
  computed: {
    ...mapState(['drawerVisible']),
    filteredLinks () {
      if (!this.filter) {
        return this.links
      }
      const filteredLinks = []
      for (let i = 0; i < this.links.length; i++) {
        if (this.links[i].permission === undefined || this.checkPermission(this.links[i].permission)) {
          if (this.links[i].separator === undefined || (filteredLinks.length > 0 && filteredLinks[filteredLinks.length - 1].separator === undefined)) {
            filteredLinks.push(this.links[i])
          }
        }
      }
      return filteredLinks
    }
  },
  methods: { }
}
</script>
