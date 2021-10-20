<template>
    <div>
        <v-row justify="center">
            <v-dialog v-model="visible" max-width="900" @keydown.esc="close" fullscreen>
                <v-card height="800">

                    <v-toolbar dark dense color="primary" data-dialog="single-detail">
                        <v-btn icon dark @click="close()" data-btn="close">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title class="title-limit">{{ news_item.title }}</v-toolbar-title>
                        <v-spacer></v-spacer>

                        <div v-if="!multiSelectActive && !analyze_selector">
                            <v-btn v-if="canDelete" small icon @click.stop="cardItemToolbar('delete')" :title="$t('assess.tooltip.delete_item')">
                                <v-icon small color="accent">mdi-delete</v-icon>
                            </v-btn>
                            <a v-if="canAccess" :href="news_item.news_items[0].news_item_data.link" target="_blank" :title="$t('assess.tooltip.open_source')">
                                <v-btn small icon>
                                    <v-icon small color="accent">mdi-open-in-app</v-icon>
                                </v-btn>
                            </a>
                            <v-btn v-if="canCreateReport" small icon @click.stop="cardItemToolbar('new')"
                                   data-btn="new" :title="$t('assess.tooltip.analyze_item')">
                                <v-icon small color="accent">mdi-file-outline</v-icon>
                            </v-btn>
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
                            <span>{{ $t('assess.source') }}</span>
                        </v-tab>
                        <v-tab href="#tab-2">
                            <span>{{ $t('assess.attributes') }}</span>
                        </v-tab>
                        <v-tab href="#tab-3">
                            <span>{{ $t('assess.comments') }}</span>
                        </v-tab>

                        <!-- TABS CONTENT -->
                        <v-tab-item value="tab-1" class="px-5">
                            <v-row justify="center" class="px-8">
                                <v-row justify="center" class="subtitle-2 info--text pt-0 ma-0">
                                    <v-flex>
                                        <v-row class="text-center">
                                            <v-col>
                                                <span
                                                    class="overline font-weight-bold">{{
                                                        $t('assess.collected')
                                                    }}</span><br>
                                                <span
                                                    class="caption">{{
                                                        news_item.news_items[0].news_item_data.collected
                                                    }}</span>
                                            </v-col>
                                            <v-col>
                                                <span
                                                    class="overline font-weight-bold">{{
                                                        $t('assess.published')
                                                    }}</span><br>
                                                <span
                                                    class="caption">{{
                                                        news_item.news_items[0].news_item_data.published
                                                    }}</span>
                                            </v-col>
                                            <v-col>
                                                <span class="overline font-weight-bold">{{ $t('assess.source') }}</span><br>
                                                <span
                                                    class="caption">{{
                                                        news_item.news_items[0].news_item_data.source
                                                    }}</span>
                                            </v-col>
                                            <v-col>
                                                <span class="overline font-weight-bold">{{ $t('assess.author') }}</span><br>
                                                <span
                                                    class="caption">{{
                                                        news_item.news_items[0].news_item_data.author
                                                    }}</span>
                                            </v-col>
                                        </v-row>
                                    </v-flex>
                                </v-row>
                                <hr style="width: calc(100%); border: 0px;">
                                <v-row class="headline">
                                    <span
                                        class="display-1 font-weight-light py-4">{{
                                            news_item.news_items[0].news_item_data.title
                                        }}</span>
                                </v-row>
                                <v-row class="py-4">
                                    <span
                                        class="body-2 grey--text text--darken-1">{{
                                            news_item.news_items[0].news_item_data.content
                                        }}</span>
                                </v-row>

                                <!-- LINKS -->
                                <v-container fluid>
                                    <v-row>
                                        <a :href="news_item.news_items[0].news_item_data.link" target="_blank">
                                            <span>{{ news_item.news_items[0].news_item_data.link }}</span>
                                        </a>
                                    </v-row>
                                </v-container>


                            </v-row>

                        </v-tab-item>

                        <v-tab-item value="tab-2" class="pa-5">
                            <NewsItemAttribute v-for="attribute in news_item.attributes" :key="attribute.id"
                                               :attribute="attribute"
                                               :news_item_data="news_item.news_items[0].news_item_data"/>
                        </v-tab-item>

                        <v-tab-item value="tab-3" class="pa-5">
                            <vue-editor
                                ref="assessDetailComments"
                                :editorOptions="editorOptionVue2"
                            />
                        </v-tab-item>

                    </v-tabs>

                </v-card>
            </v-dialog>
        </v-row>
    </div>

</template>

<script>
import {deleteNewsItemAggregate, getNewsItem, voteNewsItem} from "@/api/assess";
import {readNewsItem} from "@/api/assess";
import {importantNewsItem} from "@/api/assess";
import {saveNewsItemAggregate} from "@/api/assess";
import NewsItemAttribute from "@/components/assess/NewsItemAttribute";
import AuthMixin from "@/services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";

import {VueEditor} from 'vue2-editor';

const toolbarOptions = [
    ['bold', 'italic', 'underline', 'strike'],        // toggled buttons
    ['blockquote', 'code-block'],

    [{'header': 1}, {'header': 2}],               // custom button values
    [{'list': 'ordered'}, {'list': 'bullet'}],
    [{'script': 'sub'}, {'script': 'super'}],      // superscript/subscript
    [{'indent': '-1'}, {'indent': '+1'}],          // outdent/indent
    [{'direction': 'rtl'}],                         // text direction

    [{'size': ['small', false, 'large', 'huge']}],  // custom dropdown
    [{'header': [1, 2, 3, 4, 5, 6, false]}],

    [{'color': []}, {'background': []}],          // dropdown with defaults from theme
    [{'font': []}],
    [{'align': []}],

    ['clean'],                                         // remove formatting button
    ['link', 'image', 'video']
];

export default {
    name: "NewsItemSingleDetail",
    components: {NewsItemAttribute, VueEditor},
    mixins: [AuthMixin],
    props: {
        analyze_selector: Boolean
    },
    computed: {
        canAccess() {
            return this.checkPermission(Permissions.ASSESS_ACCESS) && this.access === true
        },

        canModify() {
            return this.checkPermission(Permissions.ASSESS_UPDATE) && this.modify === true
        },

        canDelete() {
            return this.checkPermission(Permissions.ASSESS_DELETE) && this.modify === true
        },

        canCreateReport() {
            return this.checkPermission(Permissions.ANALYZE_CREATE)
        },

        multiSelectActive() {
            return this.$store.getters.getMultiSelect
        },
    },
    data: () => ({
        content: null,
        editorOptionVue2: {
            theme: 'snow',
            placeholder: "insert text here ...",
            modules: {
                toolbar: toolbarOptions
            }
        },
        visible: false,
        access: false,
        modify: false,
        news_item: {news_items: [{news_item_data: {}}]},
        toolbar: false
    }),
    methods: {
        open(news_item) {
            this.access = news_item.news_items[0].access
            this.modify = news_item.news_items[0].modify
            if (news_item.news_items[0].access === true) {
                getNewsItem(news_item.news_items[0].id).then((response) => {
                    this.visible = true
                    this.news_item = news_item;
                    this.news_item.news_items[0] = response.data;
                    this.title = news_item.title;
                    this.description = news_item.description;
                    this.editorData = this.news_item.comments
                });
            } else {
                this.visible = true
                this.news_item = news_item;
                this.title = news_item.title;
                this.description = news_item.description;
                this.editorData = this.news_item.comments
            }

            this.$root.$emit('first-dialog', 'push');
        },
        close() {
            this.visible = false;
            if (this.canModify) {
                saveNewsItemAggregate(this.getGroupId(), this.news_item.id, this.news_item.title, this.news_item.description, this.editorData).then(() => {
                    this.news_item.comments = this.editorData
                });
            }
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

                case "new":
                    this.$root.$emit('new-report', [this.news_item]);
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
                    deleteNewsItemAggregate(this.getGroupId(), this.news_item.id).then(() => {
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
