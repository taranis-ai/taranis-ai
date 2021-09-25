<template>

    <v-layout class="navigation" align-center justify-space-between column fill-height>

        <v-list class="navigation-list pa-0">
            <v-list-item class="section-icon">
                <v-list-item-title>
                    <v-icon regular class="" color="white">{{icon}}</v-icon>
                </v-list-item-title>
            </v-list-item>
            <v-divider class="section-divider" color="white"></v-divider>

            <v-list-item dense v-for="link in filteredLinks" :key="link.id" router :to="link.route">
                <v-list-item-content v-if="!link.separator">
                    <v-icon regular color="cx-drawer-text">{{ link.icon }}</v-icon>
                    <v-list-item-title class="cx-drawer-text--text">{{ $t(link.title) }}</v-list-item-title>
                </v-list-item-content>
                <v-list-item-content class="separator" v-else>
                    <v-divider class="section-divider " color="white"></v-divider>
                </v-list-item-content>
            </v-list-item>

        </v-list>

        <v-btn justify-end text exact icon color="white">
            <v-icon>mdi-settings</v-icon>
        </v-btn>
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

<style>
    .navigation .v-list-item--active:not(.theme--dark) {
        background-color: rgba(255, 255, 255, 0.3);
    }

    .navigation .section-icon,
    .navigation .section-divider {
        opacity: 0.2;
    }

    nav .v-list-item__title {
        text-align: center;
        white-space: unset;
        font-size: 1vh;
    }

    .navigation .navigation-list div.v-list-item:not(.section-icon) {
        min-height: 10px;
    }

</style>