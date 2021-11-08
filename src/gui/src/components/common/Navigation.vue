<template>
    <v-layout class="navigation" fill-height justify-center>

        <v-list class="navigation-list pa-0" width="100">
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
</template>

<script>
    import AuthMixin from "@/services/auth/auth_mixin";

    export default {
        name: "Navigation",
        props: {
            titles: Array,
            links: Array,
            links2: Array,
            icon: String,
            filter: Boolean
        },
        mixins: [AuthMixin],
        data: () => ({}),
        computed: {
            filteredLinks() {
                if (this.filter === true) {
                    let filteredLinks = []
                    for (let i = 0; i < this.links.length; i++) {
                        if (this.links[i].permission === undefined || this.checkPermission(this.links[i].permission)) {
                            if (this.links[i].separator === undefined || (filteredLinks.length > 0 && filteredLinks[filteredLinks.length - 1].separator === undefined)) {
                                filteredLinks.push(this.links[i])
                            }
                        }
                    }

                    if (filteredLinks[0].separator !== undefined) {
                        filteredLinks.splice(0, 1)
                    }

                    if (filteredLinks[filteredLinks.length - 1].separator !== undefined) {
                        filteredLinks.splice(filteredLinks.length - 1, 1)
                    }

                    return filteredLinks
                } else {
                    return this.links
                }
            }
        },
        methods: {
            hasPermission(link) {
                return this.checkPermission(link.permission)
            }
        }
    }
</script>