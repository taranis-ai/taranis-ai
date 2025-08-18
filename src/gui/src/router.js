import { createWebHistory, createRouter } from 'vue-router'
import { useAuthStore } from './stores/AuthStore'
import Permissions from '@/services/auth/permissions'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      beforeEnter() {
        location.href = '/frontend'
      }
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
