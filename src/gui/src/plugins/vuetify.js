import Vue from 'vue'
import Vuetify from 'vuetify'
import { Scroll } from 'vuetify/lib/directives'
import awakePinSvg from '@/assets/icons/pin.vue'
import awakeSearchSvg from '@/assets/icons/search.vue'
import awakeCommentSvg from '@/assets/icons/comment.vue'
import awakeEditSvg from '@/assets/icons/edit.vue'
import awakeEyeSvg from '@/assets/icons/eye.vue'
import awakeRelatedSvg from '@/assets/icons/related.vue'
import awakeReportSvg from '@/assets/icons/report.vue'
import awakeRibbonSvg from '@/assets/icons/ribbon.vue'
import awakeUnreadSvg from '@/assets/icons/unread.vue'
import awakeDeleteSvg from '@/assets/icons/delete.vue'
import awakeMergeSvg from '@/assets/icons/merge.vue'
import awakeShareSvg from '@/assets/icons/share.vue'
import awakeShareOutlineSvg from '@/assets/icons/shareOutline.vue'
import awakeCloseSvg from '@/assets/icons/close.vue'
import awakeImportantSvg from '@/assets/icons/important.vue'
import newsItemActionDeleteSvg from '@/assets/icons/action-delete.vue'
import newsItemActionReadSvg from '@/assets/icons/action-read.vue'
import newsItemActionUnreadSvg from '@/assets/icons/action-unread.vue'
import newsItemActionRemoveSvg from '@/assets/icons/action-remove.vue'
import newsItemActionRibbonSvg from '@/assets/icons/action-ribbon.vue'
import newsItemActionImportantSvg from '@/assets/icons/action-important.vue'

Vue.use(Vuetify)

const colors = {
  primary: '#7468E8',
  secondary: '#34a5e8',
  accent: '#82B1FF',
  info: '#2196F3',
  error: '#FF5252',
  success: '#4CAF50',
  warning: '#FFC107',
  grey: '#C9C9C9',
  'cx-app-header': '#E6E6E6',
  'cx-toolbar-filter': '#ffffff',
  'cx-combo-gray': '#f2f2f2',
  'cx-user-menu': '#d9d9d9',
  'cx-drawer-bg': '#ffffff',
  'cx-drawer-text': '#000000',
  'cx-drawer-text-invert': '#000',
  'cx-line': '#fafafa',
  'cx-favorites': '#ff9d48',
  'cx-filter': '#9f02ff',
  'cx-wordlist': '#FFC107',
  'dark-grey': '#575757',
  'awake-green-color': '#77BB70',
  'awake-yellow-color': '#E9C645',
  'awake-red-color': '#D18E8E'
}

const theme = {
  themes: {
    dark: colors,
    light: colors
  }
}

const breakpoint = {
  thresholds: {
    xs: 600,
    sm: 976,
    md: 1280,
    lg: 2200
  },
  scrollBarWidth: 16
}

const icons = {
  iconfont: 'mdi',
  values: {
    awakePin: {
      component: awakePinSvg
    },
    awakeMerge: {
      component: awakeMergeSvg
    },
    awakeShare: {
      component: awakeShareSvg
    },
    awakeShareOutline: {
      component: awakeShareOutlineSvg
    },
    awakeSearch: {
      component: awakeSearchSvg
    },
    awakeEye: {
      component: awakeEyeSvg
    },
    awakeComment: {
      component: awakeCommentSvg
    },
    awakeEdit: {
      component: awakeEditSvg
    },
    awakeRelated: {
      component: awakeRelatedSvg
    },
    awakeImportant: {
      component: awakeImportantSvg
    },
    awakeUnread: {
      component: awakeUnreadSvg
    },
    awakeClose: {
      component: awakeCloseSvg
    },
    awakeReport: {
      component: awakeReportSvg
    },
    awakeRibbon: {
      component: awakeRibbonSvg
    },
    awakeDelete: {
      component: awakeDeleteSvg
    },
    newsItemActionDelete: {
      component: newsItemActionDeleteSvg
    },
    newsItemActionRead: {
      component: newsItemActionReadSvg
    },
    newsItemActionUnread: {
      component: newsItemActionUnreadSvg
    },
    newsItemActionRemove: {
      component: newsItemActionRemoveSvg
    },
    newsItemActionRibbon: {
      component: newsItemActionRibbonSvg
    },
    newsItemActionImportant: {
      component: newsItemActionImportantSvg
    }
  }
}

const directives = { Scroll }

// Set vuetify

const vuetify = new Vuetify(
  {
    directives: directives,
    breakpoint: breakpoint,
    icons: icons,
    theme: theme
  })

export default vuetify
