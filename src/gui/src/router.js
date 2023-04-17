import Vue from 'vue'
import Router from 'vue-router'
import Home from './views/Home.vue'
import { store } from '@/store/store'
import Permissions from '@/services/auth/permissions'

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
      path: '/enter',
      name: 'enter',
      components: {
        default: () =>
          import(/* webpackChunkName: "common" */ './views/users/EnterView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_CREATE] }
    },
    {
      path: '/newsitem/:id',
      name: 'newsitem',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "assess" */ './views/users/NewsItemView.vue'
          )
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/story/:id',
      name: 'story',
      components: {
        default: () =>
          import(/* webpackChunkName: "assess" */ './views/users/StoryView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/assess*',
      name: 'assess',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "assess" */ './views/users/AssessView.vue'
          ),
        nav: () =>
          import(/* webpackChunkName: "assess" */ './views/nav/AssessNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/analyze',
      alias: '/reports',
      name: 'analyze',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "analyze" */ './views/users/AnalyzeView.vue'
          ),
        nav: () =>
          import(/* webpackChunkName: "analyze" */ './views/nav/AnalyzeNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ANALYZE_ACCESS] }
    },
    {
      path: '/report/:id',
      name: 'report',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "analyze" */ './views/users/ReportView.vue'
          )
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/publish',
      alias: '/products',
      name: 'publish',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "publish" */ './views/users/PublishView.vue'
          ),
        nav: () =>
          import(/* webpackChunkName: "publish" */ './views/nav/PublishNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.PUBLISH_ACCESS] }
    },
    {
      path: '/product/:id',
      name: 'product',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "publish" */ './views/users/ProductView.vue'
          )
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/assets',
      name: 'assets',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "assets" */ './views/users/AssetsView.vue'
          ),
        nav: () =>
          import(/* webpackChunkName: "assets" */ './views/nav/AssetsNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_ACCESS] }
    },
    {
      path: '/asset/:id',
      name: 'asset',
      components: {
        default: () =>
          import(/* webpackChunkName: "assets" */ './views/users/AssetView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_ACCESS] }
    },
    {
      path: '/asset-group/:id',
      name: 'asset-group',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "assets" */ './views/users/AssetGroupView.vue'
          )
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_ACCESS] }
    },
    {
      path: '/user',
      name: 'user',
      components: {
        default: () =>
          import(/* webpackChunkName: "user" */ './views/users/UserView.vue'),
        nav: () =>
          import(/* webpackChunkName: "user" */ './views/nav/UserNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
    },
    {
      path: '/user/settings',
      name: 'user-settings',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "user" */ './views/users/SettingsView.vue'
          ),
        nav: () =>
          import(/* webpackChunkName: "user" */ './views/nav/UserNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
    },
    {
      path: '/user/templates',
      name: 'user-templates',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "user" */ './views/users/NotificationTemplatesView.vue'
          ),
        nav: () =>
          import(/* webpackChunkName: "user" */ './views/nav/UserNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
    },
    {
      path: '/config/dashboard',
      alias: '/config',
      name: 'configDashboard',
      components: {
        default: () =>
          import(
            /* webpackChunkName: "config" */ './views/admin/DashBoardConfigView.vue'
          ),
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
          import(/* webpackChunkName: "config" */ './views/admin/ACLsView.vue'),
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
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
        nav: () =>
          import(/* webpackChunkName: "config" */ './views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true
      }
    },
    {
      path: '/login',
      name: 'login',
      component: () =>
        import(/* webpackChunkName: "common" */ './views/Login.vue')
    }
  ]
})

router.beforeEach(async (to, from, next) => {
  if (to.meta.requiresAuth && !store.getters.isAuthenticated) {
    if (store.getters.hasExternalLoginUrl) {
      window.location = encodeURI(store.getters.getLoginURL)
    }
    next({ path: store.getters.getLoginURL, query: { redirect: to.path } })
  }
  next()
})
