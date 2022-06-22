import Vue from 'vue'
import Router from 'vue-router'
import Home from './views/Home.vue'
import {store} from '@/store/store'
import AuthService from "@/services/auth/auth_service";
import Permissions from "@/services/auth/permissions";

Vue.use(Router);

export const router = new Router({

    mode: 'history',
    base: process.env.BASE_URL,
    routes: [
        {
            path: '/',
            name: 'home',
            component: Home,
            meta: {requiresAuth: true, requiresPerm: []}
        },
        {
            path: '/enter*',
            name: 'enter',
            components: {
                default: () => import('./views/users/EnterView.vue'),
                nav: () => import('./views/nav/EnterNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.ASSESS_CREATE]}
        },
        {
            path: '/assess*',
            name: 'assess',
            components: {
                default: () => import('./views/users/AssessView.vue'),
                nav: () => import('./views/nav/AssessNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS]}
        },
        {
            path: '/analyze*',
            name: 'analyze',
            components: {
                default: () => import('./views/users/AnalyzeView.vue'),
                nav: () => import('./views/nav/AnalyzeNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.ANALYZE_ACCESS]}
        },
        {
            path: '/publish',
            name: 'publish',
            components: {
                default: () => import('./views/users/PublishView.vue'),
                nav: () => import('./views/nav/PublishNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.PUBLISH_ACCESS]}
        },
        {
            path: '/myassets*',
            name: 'myassets',
            components: {
                default: () => import('./views/users/MyAssetsView.vue'),
                nav: () => import('./views/nav/MyAssetsNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_ACCESS]}
        },
        {
            path: '/dashboard',
            name: 'dashboard',
            components: {
                default: () => import('./views/users/DashboardView.vue'),
                nav: () => import('./views/nav/DashboardNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS]}
        },
        {
            path: '/config/external',
            name: 'config-external',
            components: {
                default: () => import('./views/admin/ExternalConfigView.vue'),
                nav: () => import('./views/nav/ExternalConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG]}
        },
        {
            path: '/config/external/users',
            name: 'users-external',
            components: {
                default: () => import('./views/admin/ExternalUsersView.vue'),
                nav: () => import('./views/nav/ExternalConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG]}
        },
        {
            path: '/config/external/groups',
            name: 'groups-external',
            components: {
                default: () => import('./views/admin/AssetGroupsView.vue'),
                nav: () => import('./views/nav/ExternalConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG]}
        },
        {
            path: '/config/external/templates',
            name: 'templates-external',
            components: {
                default: () => import('./views/admin/NotificationTemplatesView.vue'),
                nav: () => import('./views/nav/ExternalConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.MY_ASSETS_CONFIG]}
        },
        {
            path: '/config',
            name: 'config',
            components: {
                default: () => import('./views/admin/ConfigView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_ACCESS]}
        },
        {
            path: '/config/organizations',
            name: 'organization',
            components: {
                default: () => import('./views/admin/OrganizationsView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_ORGANIZATION_ACCESS]}
        },
        {
            path: '/config/roles',
            name: 'roles',
            components: {
                default: () => import('./views/admin/RolesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_ROLE_ACCESS]}
        },
        {
            path: '/config/acls',
            name: 'acls',
            components: {
                default: () => import('./views/admin/ACLEntriesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_ACL_ACCESS]}
        },
        {
            path: '/config/users',
            name: 'users',
            components: {
                default: () => import('./views/admin/UsersView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_USER_ACCESS]}
        },
        {
            path: '/config/collectors/nodes',
            name: 'collectors-nodes',
            components: {
                default: () => import('./views/admin/CollectorsNodesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_COLLECTORS_NODE_ACCESS]}
        },
        {
            path: '/config/collectors/sources',
            name: 'osint_sources',
            components: {
                default: () => import('./views/admin/OSINTSourcesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_OSINT_SOURCE_ACCESS]}
        },
        {
            path: '/config/collectors/groups',
            name: 'osint_source_groups',
            components: {
                default: () => import('./views/admin/OSINTSourceGroupsView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_OSINT_SOURCE_GROUP_ACCESS]}
        },
        {
            path: '/config/presenters/nodes',
            name: 'presenters-nodes',
            components: {
                default: () => import('./views/admin/PresentersNodesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_PRESENTERS_NODE_ACCESS]}
        },
        {
            path: '/config/publishers/nodes',
            name: 'publishers-nodes',
            components: {
                default: () => import('./views/admin/PublishersNodesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_PUBLISHERS_NODE_ACCESS]}
        },
        {
            path: '/config/publishers/presets',
            name: 'publisher_presets',
            components: {
                default: () => import('./views/admin/PublisherPresetsView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_PUBLISHER_PRESET_ACCESS]}
        },
        {
            path: '/config/remote/access',
            name: 'remote-access',
            components: {
                default: () => import('./views/admin/RemoteAccessesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_REMOTE_ACCESS_ACCESS]}
        },
        {
            path: '/config/remote/NODES',
            name: 'remote-nodes',
            components: {
                default: () => import('./views/admin/RemoteNodesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_REMOTE_NODE_ACCESS]}
        },
        {
            path: '/config/bots/nodes',
            name: 'bots-nodes',
            components: {
                default: () => import('./views/admin/BotsNodesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_BOTS_NODE_ACCESS]}
        },
        {
            path: '/config/bots/presets',
            name: 'bot_presets',
            components: {
                default: () => import('./views/admin/BotPresetsView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_BOT_PRESET_ACCESS]}
        },
        {
            path: '/config/product/types',
            name: 'product_types',
            components: {
                default: () => import('./views/admin/ProductTypesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_PRODUCT_TYPE_ACCESS]}
        },
        {
            path: '/config/reportitems/attributes',
            name: 'attributes',
            components: {
                default: () => import('./views/admin/AttributesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_ATTRIBUTE_ACCESS]}
        },
        {
            path: '/config/reportitems/types',
            name: 'report_types',
            components: {
                default: () => import('./views/admin/ReportTypesView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_REPORT_TYPE_ACCESS]}
        },
        {
            path: '/config/wordlists',
            name: 'word_lists',
            components: {
                default: () => import('./views/admin/WordListsView.vue'),
                nav: () => import('./views/nav/ConfigNav.vue')

            },
            meta: {requiresAuth: true, requiresPerm: [Permissions.CONFIG_WORD_LIST_ACCESS]}
        },
        {
            path: '/login',
            name: 'login',
            component: () => import('./views/Login.vue')
        }
    ]
});

router.beforeEach((to, from, next) => {

    if (to.matched.some(record => record.meta.requiresAuth)) {

        if (!AuthService.isAuthenticated()) {

            if (!store.getters.hasExternalLoginUrl) {

                next({
                    path: store.getters.getLoginURL,
                    query: {redirect: to.path}
                })
            } else {

                window.location = store.getters.getLoginURL;
            }
        } else if (to.path === "/") {
            if (AuthService.hasPermission(Permissions.ASSESS_ACCESS)) {
                next({path: "/dashboard"})
            } else if (AuthService.hasPermission(Permissions.CONFIG_ACCESS)) {
                next({path: "/config"})
            } else if (AuthService.hasPermission(Permissions.MY_ASSETS_ACCESS)) {
                next({path: "/myassets"})
            } else if (AuthService.hasPermission(Permissions.MY_ASSETS_CONFIG)) {
                next({path: "/config/external"})
            }
        } else {
            if (to.meta.requiresPerm.length > 0) {
                if (AuthService.hasAnyPermission(to.meta.requiresPerm)) {
                    next()
                } else {
                    next({path: "/"})
                }
            } else {
                next()
            }
        }
    } else {
        next()
    }
});