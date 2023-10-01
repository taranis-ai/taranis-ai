import { createWebHistory, createRouter } from 'vue-router'
import Home from '@/views/Home.vue'
import { useAuthStore } from './stores/AuthStore'
import Permissions from '@/services/auth/permissions'

export const router = createRouter({
  history: createWebHistory(),
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
        default: () => import('@/views/users/EnterView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_CREATE] }
    },
    {
      path: '/newsitem/:id',
      name: 'newsitem',
      components: {
        default: () => import('@/views/users/NewsItemView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/story/:id',
      name: 'story',
      components: {
        default: () => import('@/views/users/StoryView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/assess',
      name: 'assess',
      components: {
        default: () => import('@/views/users/AssessView.vue'),
        nav: () => import('@/views/nav/AssessNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/analyze',
      alias: '/reports',
      name: 'analyze',
      components: {
        default: () => import('@/views/users/AnalyzeView.vue'),
        nav: () => import('@/views/nav/AnalyzeNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ANALYZE_ACCESS] }
    },
    {
      path: '/report/:id',
      name: 'report',
      components: {
        default: () => import('@/views/users/ReportView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/publish',
      alias: '/products',
      name: 'publish',
      components: {
        default: () => import('@/views/users/PublishView.vue'),
        nav: () => import('@/views/nav/PublishNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.PUBLISH_ACCESS] }
    },
    {
      path: '/product/:id',
      name: 'product',
      components: {
        default: () => import('@/views/users/ProductView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
    },
    {
      path: '/assets',
      name: 'assets',
      components: {
        default: () => import('@/views/users/AssetsView.vue'),
        nav: () => import('@/views/nav/AssetsNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_ACCESS] }
    },
    {
      path: '/asset/:id',
      name: 'asset',
      components: {
        default: () => import('@/views/users/AssetView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_ACCESS] }
    },
    {
      path: '/asset-group/:id',
      name: 'asset-group',
      components: {
        default: () => import('@/views/users/AssetGroupView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_ACCESS] }
    },
    {
      path: '/cluster/:cluster',
      name: 'cluster',
      components: {
        default: () => import('@/views/users/ClusterView.vue')
      }
    },
    {
      path: '/user',
      name: 'user',
      components: {
        default: () => import('@/views/users/settings/UserView.vue'),
        nav: () => import('@/views/nav/UserNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
    },
    {
      path: '/user/settings',
      name: 'user-settings',
      components: {
        default: () => import('@/views/users/settings/UserSettings.vue'),
        nav: () => import('@/views/nav/UserNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG] }
    },
    {
      path: '/config/dashboard',
      alias: '/config',
      name: 'configDashboard',
      components: {
        default: () => import('@/views/admin/DashBoardConfigView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: [Permissions.CONFIG_ACCESS] }
    },
    {
      path: '/config/organizations',
      name: 'organization',
      components: {
        default: () => import('@/views/admin/OrganizationsView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
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
        default: () => import('@/views/admin/RolesView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
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
        default: () => import('@/views/admin/ACLsView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
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
        default: () => import('@/views/admin/UsersView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_USER_ACCESS]
      }
    },
    {
      path: '/config/workers',
      name: 'workers',
      components: {
        default: () => import('@/views/admin/WorkersView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_WORKER_ACCESS]
      }
    },
    {
      path: '/config/bots',
      name: 'bots',
      components: {
        default: () => import('@/views/admin/BotsView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_BOT_ACCESS]
      }
    },
    {
      path: '/config/sources',
      name: 'osint_sources',
      components: {
        default: () => import('@/views/admin/OSINTSourcesView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_OSINT_SOURCE_ACCESS]
      }
    },
    {
      path: '/config/sourcegroups',
      name: 'osint_source_groups',
      components: {
        default: () => import('@/views/admin/OSINTSourceGroupsView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
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
        default: () => import('@/views/admin/PublisherPresetsView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_PUBLISHER_PRESET_ACCESS]
      }
    },
    {
      path: '/config/product/types',
      name: 'product_types',
      components: {
        default: () => import('@/views/admin/ProductTypesView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
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
        default: () => import('@/views/admin/AttributesView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
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
        default: () => import('@/views/admin/ReportTypesView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
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
        default: () => import('@/views/admin/WordListsView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_WORD_LIST_ACCESS]
      }
    },
    {
      path: '/config/workertypes',
      name: 'worker_types',
      components: {
        default: () => import('@/views/admin/WorkerTypesView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: [Permissions.CONFIG_BOT_ACCESS]
      }
    },
    {
      path: '/config/openapi',
      name: 'openapi',
      components: {
        default: () => import('@/views/admin/OpenAPI.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true
      }
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue')
    }
  ]
})

router.beforeEach((to) => {
  const authstore = useAuthStore()
  if (to.meta.requiresAuth && !authstore.isAuthenticated) {
    if (authstore.external_login_uri) {
      window.location = encodeURI(authstore.login_uri)
    }
    return { name: 'login' }
  }
  return true
})
