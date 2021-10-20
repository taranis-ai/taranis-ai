<template>
    <div>
        <v-row justify="center">
            <v-dialog v-model="visible" max-width="900" @keydown.esc="close" fullscreen>
                <v-card height="800">

                    <v-toolbar dark dense color="primary" data-dialog="item-detail">
                        <v-btn icon dark @click="close()" data-btn="close">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title class="title-limit">{{news_item.news_item_data.title}}</v-toolbar-title>
                        <v-spacer></v-spacer>

                        <div v-if="!multiSelectActive && !analyze_selector">
                            <v-btn v-if="canModify" small icon @click.stop="cardItemToolbar('ungroup')" :title="$t('assess.tooltip.ungroup_item')">
                                <v-icon small color="accent">mdi-ungroup</v-icon>
                            </v-btn>
                            <v-btn v-if="canDelete" small icon @click.stop="cardItemToolbar('delete')" :title="$t('assess.tooltip.delete_item')">
                                <v-icon small color="accent">mdi-delete</v-icon>
                            </v-btn>
                            <a v-if="canAccess" :href="news_item.news_item_data.link" target="_blank" :title="$t('assess.tooltip.open_source')">
                                <v-btn small icon>
                                    <v-icon small color="accent">mdi-open-in-app</v-icon>
                                </v-btn>
                            </a>
                            <v-btn v-if="canModify" small icon @click.stop="cardItemToolbar('read')" :title="$t('assess.tooltip.read_item')">
                                <v-icon small :color="buttonStatus(news_item.read)">mdi-eye</v-icon>
                            </v-btn>
                            <v-btn v-if="canModify" small icon @click.stop="cardItemToolbar('important')" :title="$t('assess.tooltip.important_item')">
                                <v-icon small :color="buttonStatus(news_item.important)">mdi-star</v-icon>
                            </v-btn>
                            <v-btn v-if="canModify" small icon @click.stop="cardItemToolbar('like')" :title="$t('assess.tooltip.like_item')">
                                <v-icon small :color="buttonStatus(news_item.me_like)">mdi-thumb-up</v-icon>
                            </v-btn>
                            <v-btn v-if="canModify" small icon @click.stop="cardItemToolbar('unlike')" :title="$t('assess.tooltip.dislike_item')">
                                <v-icon small :color="buttonStatus(news_item.me_dislike)">mdi-thumb-down</v-icon>
                            </v-btn>
                        </div>

                    </v-toolbar>

                    <v-tabs dark centered grow>
                        <!-- TABS -->
                        <v-tab href="#tab-1">
                            <span>{{$t('assess.source')}}</span>
                        </v-tab>
                        <v-tab href="#tab-2">
                            <span>{{$t('assess.attributes')}}</span>
                        </v-tab>

                        <!-- TABS CONTENT -->
                        <v-tab-item value="tab-1" class="px-5">
                            <v-row justify="center" class="px-8">
                                <v-row justify="center" class="subtitle-2 info--text pt-0 ma-0">
                                    <v-flex>
                                        <v-row class="text-center">
                                            <v-col>
                                                <span class="overline font-weight-bold">{{$t('assess.collected')}}</span><br>
                                                <span class="caption">{{news_item.news_item_data.collected}}</span>
                                            </v-col>
                                            <v-col>
                                                <span class="overline font-weight-bold">{{$t('assess.published')}}</span><br>
                                                <span class="caption">{{news_item.news_item_data.published}}</span>
                                            </v-col>
                                            <v-col>
                                                <span class="overline font-weight-bold">{{$t('assess.source')}}</span><br>
                                                <span class="caption">{{news_item.news_item_data.source}}</span>
                                            </v-col>
                                            <v-col>
                                                <span class="overline font-weight-bold">{{$t('assess.author')}}</span><br>
                                                <span class="caption">{{news_item.news_item_data.author}}</span>
                                            </v-col>
                                        </v-row>
                                    </v-flex>
                                </v-row>
                                <hr style="width: calc(100%); border: 0px;">
                                <v-row class="headline">
                                    <span class="display-1 font-weight-light py-4">{{news_item.news_item_data.title}}</span>
                                </v-row>
                                <v-row class="py-4">
                                    <span class="body-2 grey--text text--darken-1">{{news_item.news_item_data.content}}</span>
                                </v-row>

                                <!-- LINKS -->
                                <v-container fluid>
                                    <v-row>
                                        <a :href="news_item.news_item_data.link" target="_blank">
                                            <span>{{news_item.news_item_data.link}}</span>
                                        </a>
                                    </v-row>
                                </v-container>


                            </v-row>

                        </v-tab-item>
                        <v-tab-item value="tab-2" class="pa-5">
                            <NewsItemAttribute v-for="attribute in news_item.attributes" :key="attribute.id"
                            :attribute="attribute" :news_item_data="this.news_item.news_item_data"/>
                        </v-tab-item>

                    </v-tabs>

                </v-card>
            </v-dialog>
        </v-row>
    </div>

</template>

<script>
    import {deleteNewsItem, groupAction, voteNewsItem} from "@/api/assess";
    import {readNewsItem} from "@/api/assess";
    import {importantNewsItem} from "@/api/assess";
    import {getNewsItem} from "@/api/assess";
    import NewsItemAttribute from "@/components/assess/NewsItemAttribute";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewsItemDetail",
        components: {NewsItemAttribute},
        mixins: [AuthMixin],
        props: {
            analyze_selector: Boolean,
        },
        data: () => ({
            visible: false,
            news_item: {news_item_data:{}},
            toolbar: false
        }),
        computed: {
            canAccess() {
                return this.checkPermission(Permissions.ASSESS_ACCESS) && this.news_item.access === true
            },

            canModify() {
                return this.checkPermission(Permissions.ASSESS_UPDATE) && this.news_item.modify === true
            },

            canDelete() {
                return this.checkPermission(Permissions.ASSESS_DELETE) && this.news_item.modify === true
            },

            canCreateReport() {
                return this.checkPermission(Permissions.ANALYZE_CREATE)
            },

            multiSelectActive() {
                return this.$store.getters.getMultiSelect
            },
        },
        methods: {
            open(news_item) {
                getNewsItem(news_item.id).then((response) => {
                    this.news_item = response.data;
                    this.news_item.access = news_item.access
                    this.news_item.modify = news_item.modify
                    this.visible = true;
                });

                this.$root.$emit('first-dialog', 'push');
            },
            close() {
                this.visible = false;
                this.$root.$emit('first-dialog', '');
            },
            openUrlToNewTab: function (url) {
                window.open(url, "_blank");
            },
            getGroupId() {
                if (window.location.pathname.includes("/group/")) {
                    let i = window.location.pathname.indexOf("/group/");
                    let len = window.location.pathname.length;
                    return window.location.pathname.substring(i + 7, len);
                } else {
                    return null;
                }
            },
            cardItemToolbar(action) {
                switch (action) {
                    case "like":
                        voteNewsItem(this.getGroupId(), this.news_item.id, 1).then(() => {
                            if (this.news_item.me_like === false) {
                                this.news_item.me_like = true;
                                this.news_item.me_dislike = false;
                            }
                        });
                        break;

                    case "unlike":
                        voteNewsItem(this.getGroupId(), this.news_item.id, -1).then(() => {
                            if (this.news_item.me_dislike === false) {
                                this.news_item.me_like = false;
                                this.news_item.me_dislike = true;
                            }
                        });
                        break;

                    case "detail":
                        this.toolbar = false;
                        this.itemClicked(this.card);
                        break;

                    case "important":
                        importantNewsItem(this.getGroupId(), this.news_item.id).then(() => {
                            this.news_item.important = this.news_item.important === false;
                        });
                        break;

                    case "read":
                        readNewsItem(this.getGroupId(), this.news_item.id).then(() => {
                            this.news_item.read = this.news_item.read === false;
                        });
                        break;

                    case "delete":
                        deleteNewsItem(this.getGroupId(), this.news_item.id).then(() => {
                            this.visible = false;
                        });
                        break;

                    case "ungroup":
                        groupAction({
                            'group': this.getGroupId(),
                            'action': 'UNGROUP',
                            'items': [{'type': 'ITEM', 'id': this.news_item.id}]
                        }).then(() => {
                            this.visible = false;
                        });
                        break;

                    default:
                        this.toolbar = false;
                        //this.itemClicked(this.card);
                        break;
                }
            },

            buttonStatus: function (active) {
                if (active) {
                    return "primary:lighten"
                } else {
                    return "accent"
                }
            }
        }
    }
</script>

<style>
    [role='tablist'] {
        top: 48px;
    }
    .title-limit {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 550px;
        font-size: 1em;
    }
</style>
