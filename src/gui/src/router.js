import { createWebHistory, createRouter } from 'vue-router'
import Home from '@/views/Home.vue'
import { useAuthStore } from './stores/AuthStore'
import Permissions from '@/services/auth/permissions'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
      meta: { requiresAuth: true }
    },
    {
      path: '/assess',
      name: 'assess',
      components: {
        default: () => import('@/views/users/AssessView.vue'),
        nav: () => import('@/views/nav/AssessNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.ASSESS_ACCESS,
        title: 'Assess'
      }
    },
    {
      path: '/enter/:storyId?',
      name: 'enter',
      components: {
        default: () => import('@/views/users/EnterView.vue')
      },
      props: true,
      meta: { requiresAuth: true, requiresPerm: Permissions.ASSESS_CREATE }
    },
    {
      path: '/newsitem/:itemId',
      name: 'newsitem',
      components: {
        default: () => import('@/views/users/NewsItemView.vue')
      },
      props: true,
      meta: { requiresAuth: true, requiresPerm: Permissions.ASSESS_ACCESS }
    },
    {
      path: '/newsitem/:itemId/edit',
      name: 'newsitemedit',
      components: {
        default: () => import('@/views/users/NewsItemEditView.vue')
      },
      props: true,
      meta: { requiresAuth: true, requiresPerm: Permissions.ASSESS_UPDATE }
    },
    {
      path: '/story/:storyId',
      name: 'story',
      components: {
        default: () => import('@/views/users/StoryView.vue')
      },
      props: true,
      meta: { requiresAuth: true, requiresPerm: Permissions.ASSESS_ACCESS }
    },
    {
      path: '/story/:storyId/edit',
      name: 'storyedit',
      components: {
        default: () => import('@/views/users/StoryEditView.vue')
      },
      props: true,
      meta: { requiresAuth: true, requiresPerm: Permissions.ASSESS_UPDATE }
    },
    {
      path: '/analyze',
      alias: '/reports',
      name: 'analyze',
      components: {
        default: () => import('@/views/users/AnalyzeView.vue'),
        nav: () => import('@/views/nav/AnalyzeNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.ANALYZE_ACCESS,
        title: 'Analyze'
      }
    },
    {
      path: '/report/:reportId?',
      name: 'report',
      components: {
        default: () => import('@/views/users/ReportView.vue')
      },
      props: true,
      meta: { requiresAuth: true, requiresPerm: Permissions.ASSESS_ACCESS },
      title: 'Analyze'
    },
    {
      path: '/publish',
      alias: '/products',
      name: 'publish',
      components: {
        default: () => import('@/views/users/PublishView.vue'),
        nav: () => import('@/views/nav/PublishNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.PUBLISH_ACCESS,
        title: 'Publish'
      }
    },
    {
      path: '/product/:productId?',
      name: 'product',
      components: {
        default: () => import('@/views/users/ProductView.vue')
      },
      props: true,
      meta: { requiresAuth: true, requiresPerm: Permissions.ASSESS_ACCESS }
    },
    {
      path: '/assets',
      name: 'assets',
      components: {
        default: () => import('@/views/users/AssetsView.vue'),
        nav: () => import('@/views/nav/AssetsNav.vue')
      },
      meta: { requiresAuth: true, requiresPerm: Permissions.ASSETS_ACCESS }
    },
    {
      path: '/asset/:id?',
      name: 'asset',
      components: {
        default: () => import('@/views/users/AssetView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: Permissions.ASSETS_ACCESS }
    },
    {
      path: '/asset-group/:id?',
      name: 'asset-group',
      components: {
        default: () => import('@/views/users/AssetGroupView.vue')
      },
      meta: { requiresAuth: true, requiresPerm: Permissions.ASSETS_ACCESS }
    },
    {
      path: '/connectors',
      name: 'connector-user-access',
      components: {
        default: () => import('@/views/users/ConflictsView.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONNECTOR_USER_ACCESS
      }
    },
    {
      path: '/cluster/:cluster',
      name: 'cluster',
      props: true,
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
      meta: { requiresAuth: true }
    },
    {
      path: '/user/settings',
      name: 'user-settings',
      components: {
        default: () => import('@/views/users/settings/UserSettings.vue'),
        nav: () => import('@/views/nav/UserNav.vue')
      },
      meta: { requiresAuth: true }
    },
    {
      path: '/config/dashboard',
      alias: '/config',
      name: 'configDashboard',
      components: {
        default: () => import('@/views/admin/FrontendProxy.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      props: {
        default: {
          title: 'Dashboard',
          targetUrl: `${import.meta.env.BASE_URL}frontend/admin`
        }
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONFIG_ACCESS
      }
    },
    {
      path: '/config/organizations',
      name: 'organization',
      components: {
        default: () => import('@/views/admin/FrontendProxy.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      props: {
        default: {
          title: 'Organizations',
          targetUrl: `${import.meta.env.BASE_URL}frontend/admin/organizations`
        }
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONFIG_ORGANIZATION_ACCESS
      }
    },
    {
      path: '/config/roles',
      name: 'roles',
      components: {
        default: () => import('@/views/admin/FrontendProxy.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      props: {
        default: {
          title: 'Roles',
          targetUrl: `${import.meta.env.BASE_URL}frontend/admin/roles`
        }
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONFIG_ROLE_ACCESS
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
        requiresPerm: Permissions.CONFIG_ACL_ACCESS
      }
    },
    {
      path: '/config/users',
      name: 'users',
      components: {
        default: () => import('@/views/admin/FrontendProxy.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      props: {
        default: {
          title: 'Users',
          targetUrl: `${import.meta.env.BASE_URL}frontend/admin/users`
        }
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONFIG_USER_ACCESS
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
        requiresPerm: Permissions.CONFIG_WORKER_ACCESS
      }
    },
    {
      path: '/config/scheduler',
      name: 'scheduler',
      components: {
        default: () => import('@/views/admin/FrontendProxy.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      props: {
        default: {
          title: 'Scheduler',
          targetUrl: `${import.meta.env.BASE_URL}frontend/admin/scheduler`
        }
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONFIG_WORKER_ACCESS
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
        requiresPerm: Permissions.CONFIG_BOT_ACCESS
      }
    },
    {
      path: '/config/connectors',
      name: 'connectors',
      components: {
        default: () => import('@/views/admin/ConnectorsView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONFIG_CONNECTOR_ACCESS
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
        requiresPerm: Permissions.CONFIG_OSINT_SOURCE_ACCESS
      }
    },
    {
      path: '/config/sources/:source_id',
      name: 'osint_sources_preview',
      components: {
        default: () => import('@/views/admin/OSINTSourcesPreview.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONFIG_OSINT_SOURCE_ACCESS
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
        requiresPerm: Permissions.CONFIG_OSINT_SOURCE_GROUP_ACCESS
      }
    },
    {
      path: '/config/publishers',
      name: 'publisher',
      components: {
        default: () => import('@/views/admin/PublisherView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONFIG_PUBLISHER_ACCESS
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
        requiresPerm: Permissions.CONFIG_PRODUCT_TYPE_ACCESS
      }
    },
    {
      path: '/config/product/templates',
      name: 'product_templates',
      components: {
        default: () => import('@/views/admin/ProductTemplatesView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONFIG_PRODUCT_TYPE_ACCESS
      }
    },
    {
      path: '/config/attributes',
      name: 'attributes',
      components: {
        default: () => import('@/views/admin/AttributesView.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.CONFIG_ATTRIBUTE_ACCESS
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
        requiresPerm: Permissions.CONFIG_REPORT_TYPE_ACCESS
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
        requiresPerm: Permissions.CONFIG_WORD_LIST_ACCESS
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
        requiresPerm: Permissions.CONFIG_BOT_ACCESS
      }
    },
    {
      path: '/config/openapi',
      name: 'openapi',
      components: {
        default: () => import('@/views/admin/FrontendProxy.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      props: {
        default: {
          title: 'OpenAPI',
          targetUrl: `${import.meta.env.BASE_URL}frontend/doc`
        }
      },
      meta: {
        requiresAuth: true
      }
    },
    {
      path: '/config/settings',
      name: 'admin-settings',
      components: {
        default: () => import('@/views/admin/FrontendProxy.vue'),
        nav: () => import('@/views/nav/ConfigNav.vue')
      },
      props: {
        default: {
          title: 'Settings',
          targetUrl: `${import.meta.env.BASE_URL}frontend/admin/settings`
        }
      },
      meta: {
        requiresAuth: true,
        requiresPerm: Permissions.ADMIN_OPERATIONS
      }
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue')
    },
    {
      path: '/403',
      name: 'forbidden',
      component: () => import('@/views/error/AccessForbidden.vue')
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/error/NotFound.vue')
    }
  ]
})

router.beforeEach((to) => {
  const authstore = useAuthStore()
  if (to.meta.requiresAuth && !authstore.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.meta.requiresPerm && !authstore.hasAccess(to.meta.requiresPerm)) {
    console.error('Access Denied - User is lacking permissions')
    return { name: 'forbidden' }
  }
  if (to.meta.title) {
    document.title = `Taranis AI | ${to.meta.title}`
  } else {
    document.title = 'Taranis AI'
  }

  return true
})
