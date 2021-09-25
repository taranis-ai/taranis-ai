<template>
    <v-hover v-slot:default="{hover}" close-delay="150">
        <v-card flat class="card mb-1" :elevation="hover ? 12 : 2"
                @click.stop="cardItemToolbar"
                @mouseenter.native="toolbar=true"
                @mouseleave.native="toolbar=false"
        >
            <v-layout row wrap class="pa-3 pl-0 status" v-bind:class="itemStatus">
                <v-row justify="center" style="width: 100%;">
                    <v-flex md1 class="obj center">
                        <div class="caption grey--text"><br/></div>
                        <div>
                            <v-icon center>{{card.tag}}</v-icon>
                        </div>
                    </v-flex>
                    <v-flex md5>
                        <div class="caption grey--text">{{$t('card_item.title')}}</div>
                        <span>{{card.title}}</span>
                    </v-flex>
                    <v-flex md5>
                        <div class="caption grey--text ">{{$t('card_item.description')}}</div>
                        <span class="font-weight-light caption">{{card.subtitle}}</span>
                    </v-flex>
                    <v-flex md1 class="obj center">
                        <v-speed-dial v-if="deleteAllowed()"
                                      v-model="toolbar"
                                      direction="left"
                                      transition='slide-x-reverse-transition'
                        >

                            <v-btn fab x-small color="red" @click.stop="cardItemToolbar('delete')">
                                <v-icon color="white">mdi-trash-can-outline</v-icon>
                            </v-btn>
                        </v-speed-dial>
                    </v-flex>
                </v-row>
                <v-row style="width: 100%;">
                    <span class="pl-4 pt-1">
                            <v-btn v-if="card.vulnerabilities_count > 0" depressed x-small
                                   color="red lighten-4">
                                {{$t('asset.vulnerabilities_count') + card.vulnerabilities_count}}
                            </v-btn>
                            <v-btn v-if="card.vulnerabilities_count === 0" depressed x-small>
                                {{$t('asset.no_vulnerabilities') }}
                            </v-btn>
                    </span>
                </v-row>
            </v-layout>
        </v-card>
    </v-hover>
</template>

<script>
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "CardAsset",
        props: {
            card: Object,
        },

        data: () => ({
            toolbar: false,
            selected: false,
            status: "in_progress"
        }),
        mixins: [AuthMixin],
        computed: {
            itemStatus: function () {
                if (this.card.vulnerabilities_count > 0) {
                    return "alert"
                } else {
                    return "completed"
                }
            }
        },
        methods: {
            itemClicked(data) {
                this.$root.$emit('show-edit', data);
            },
            deleteClicked(data) {
                this.$root.$emit('delete-asset', data)
            },
            deleteAllowed() {
                return this.checkPermission(Permissions.MY_ASSETS_CREATE)
            },
            cardItemToolbar(action) {
                switch (action) {
                    case "edit":
                        break;

                    case "delete":
                        this.deleteClicked(this.card);
                        break;

                    default:
                        this.toolbar = false;
                        this.itemClicked(this.card);
                        break;
                }
            }
        }
    }
</script>

<style>
    .card .obj.center {
        text-align: center;
    }

    .card.elevation-12 {
        z-index: 1;
        background-color: rgba(100, 137, 214, 0.1);
    }

    .card .status.in_progress {
        border-left: 4px solid #ffd556;
    }

    .card .status.completed {
        border-left: 4px solid #33DD40;
    }

    .card .status.alert {
        border-left: 4px solid red;
    }
</style>