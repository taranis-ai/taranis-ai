import Vue from 'vue'
import Router from 'vue-router'
import Home from './views/Home.vue'
import { store } from '@/store/store'
import AuthService from '@/services/auth/auth_service'
import Permissions from '@/services/auth/permissions'
import AssessNav from '@/views/nav/AssessNav.vue'
import EnterNav from '@/views/nav/EnterNav.vue'
import AnalyzeNav from '@/views/nav/AnalyzeNav.vue'
import PublishNav from '@/views/nav/PublishNav.vue'
import MyAssetsNav from '@/views/nav/MyAssetsNav.vue'
import ConfigNav from '@/views/nav/ConfigNav.vue'
import UserNav from '@/views/nav/UserNav.vue'

Vue.use(Router)

export const router = new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
      meta: { requiresAuth: true, requiresPerm: [] }
    },
    {
      path: '/enter*',
      name: 'enter',
      components: {
        default: () => import(/* webpackChunkName: "common" */ './views/users/EnterView.vue'),
        nav: EnterNav
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_CREATE] }
    },
    {
      path: '/assess*',
      name: 'assess',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "assess" */ './views/users/AssessView.vue'
          ),
        nav: AssessNav
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/analyze*',
      name: 'analyze',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "analyze" */ './views/users/AnalyzeView.vue'
          ),
        nav: AnalyzeNav
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ANALYZE_ACCESS] }
    },
    {
      path: '/publish',
      name: 'publish',
      components: {
        default: () => import(/* webpackChunkName: "publish" */ './views/users/PublishView.vue'),
        nav: PublishNav
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.PUBLISH_ACCESS] }
    },
    {
      path: '/myassets*',
      name: 'myassets',
      components: {
        default: () => import(/* webpackChunkName: "assets" */ './views/users/MyAssetsView.vue'),
        nav: MyAssetsNav
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_ACCESS] }
    },
    {
      path: '/user',
      name: 'user',
      components: {
        default: () => import(/* webpackChunkName: "user" */ './views/users/UserView.vue'),
        nav: UserNav
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
    },
    {
      path: '/user/settings',
      name: 'user-settings',
      components: {
        default: () => import(/* webpackChunkName: "user" */ './views/users/SettingsView.vue'),
        nav: UserNav
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
    },
    {
      path: '/user/templates',
      name: 'user-templates',
      components: {
        default: () => import(/* webpackChunkName: "user" */ './views/users/NotificationTemplatesView.vue'),
        nav: UserNav
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
    },
    {
      path: '/user/assets',
      name: 'user-assets',
      components: {
        default: () => import(/* webpackChunkName: "user" */ './views/users/AssetGroupsView.vue'),
        nav: UserNav
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
    },
    {
      path: '/config',
      name: 'config',
      redirect: '/config/dashboard'
    },
    {
      path: '/config/dashboard',
      name: 'configDashboard',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/DashBoardConfigView.vue'
          ),
        nav: ConfigNav
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_ACCESS] }
    },
    {
      path: '/config/organizations',
      name: 'organization',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/OrganizationsView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_ORGANIZATION_ACCESS]
      }
    },
    {
      path: '/config/roles',
      name: 'roles',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/RolesView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_ROLE_ACCESS]
      }
    },
    {
      path: '/config/acls',
      name: 'acls',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/ACLEntriesView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_ACL_ACCESS]
      }
    },
    {
      path: '/config/users',
      name: 'users',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/UsersView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_USER_ACCESS]
      }
    },
    {
      path: '/config/nodes',
      name: 'nodes',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/NodesView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_NODE_ACCESS]
      }
    },
    {
      path: '/config/collectors/sources',
      name: 'osint_sources',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/OSINTSourcesView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_OSINT_SOURCE_ACCESS]
      }
    },
    {
      path: '/config/collectors/groups',
      name: 'osint_source_groups',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/OSINTSourceGroupsView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_OSINT_SOURCE_GROUP_ACCESS]
      }
    },
    {
      path: '/config/publishers/presets',
      name: 'publisher_presets',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/PublisherPresetsView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_PUBLISHER_PRESET_ACCESS]
      }
    },
    {
      path: '/config/remote/access',
      name: 'remote-access',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/RemoteAccessesView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_REMOTE_ACCESS_ACCESS]
      }
    },
    {
      path: '/config/remote/nodes',
      name: 'remote-nodes',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/RemoteNodesView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_REMOTE_NODE_ACCESS]
      }
    },
    {
      path: '/config/product/types',
      name: 'product_types',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/ProductTypesView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_PRODUCT_TYPE_ACCESS]
      }
    },
    {
      path: '/config/reportitems/attributes',
      name: 'attributes',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/AttributesView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_ATTRIBUTE_ACCESS]
      }
    },
    {
      path: '/config/reportitems/types',
      name: 'report_types',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/ReportTypesView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_REPORT_TYPE_ACCESS]
      }
    },
    {
      path: '/config/wordlists',
      name: 'word_lists',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/WordListsView.vue'
          ),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_WORD_LIST_ACCESS]
      }
    },
    {
      path: '/config/bots',
      name: 'bots',
      components: {
        default: () =>
          import(/* webpackChunkName: "config" */ './views/admin/BotsView.vue'),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_BOT_PRESET_ACCESS]
      }
    },
    {
      path: '/config/openapi',
      name: 'openapi',
      components: {
        default: () =>
          import(/* webpackChunkName: "config" */ './views/admin/OpenAPI.vue'),
        nav: ConfigNav
      },
      meta: {
        requiresAuth: true
      }
    },
    {
      path: '/login',
      name: 'login',
      component: () => import(/* webpackChunkName: "common" */ './views/Login.vue')
    }
  ]
})

router.beforeEach((to, from, next) => {
  if (to.matched.some((record) => record.meta.requiresAuth)) {
    if (!AuthService.isAuthenticated()) {
      if (!store.getters.hasExternalLoginUrl) {
        next({ path: store.getters.getLoginURL, query: { redirect: to.path } })
      } else {
        const loginURL = store.getters.getLoginURL
          ? store.getters.getLoginURL
          : '/login'
        window.location = encodeURI(loginURL)
      }
    } else {
      next()
    }
  } else {
    next()
  }
})
