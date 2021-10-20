<template>
    <div>
        <v-row justify="center">
            <v-dialog v-model="visible" max-width="900" @keydown.esc="close" fullscreen>
                <v-card height="800">

                    <v-toolbar dark dense color="primary" data-dialog="aggregate-detail">
                        <v-btn icon dark @click="close()" data-btn="close">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title class="title-limit">{{$t('assess.aggregate_detail')}}</v-toolbar-title>
                        <v-spacer></v-spacer>

                        <div v-if="!multiSelectActive && !analyze_selector">
                            <v-btn v-if="canModify" small icon @click.stop="cardItemToolbar('ungroup')" :title="$t('assess.tooltip.ungroup_item')">
                                <v-icon small color="accent">mdi-ungroup</v-icon>
                            </v-btn>
                            <v-btn v-if="canDelete" small icon @click.stop="cardItemToolbar('delete')" :title="$t('assess.tooltip.delete_item')">
                                <v-icon small color="accent">mdi-delete</v-icon>
                            </v-btn>
                            <v-btn v-if="canCreateReport" small icon @click.stop="cardItemToolbar('new')" :title="$t('assess.tooltip.analyze_item')">
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
                            <span>{{$t('assess.aggregate_info')}}</span>
                        </v-tab>
                        <v-tab href="#tab-2">
                            <span>{{$t('assess.comments')}}</span>
                        </v-tab>

                        <!-- TABS CONTENT -->
                        <v-tab-item value="tab-1" class="px-5">
                            <v-form id="form" ref="form" style="padding:8px">
                                <v-text-field
                                        :label="$t('assess.title')"
                                        name="title"
                                        v-model="title"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-textarea
                                        :label="$t('assess.description')"
                                        name="description"
                                        v-model="description"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-textarea>
                            </v-form>
                        </v-tab-item>
                        <v-tab-item value="tab-2" class="pa-5">
                            <vue-editor
                                    ref="assessAggregateDetailComments"
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
    import {deleteNewsItemAggregate, groupAction, voteNewsItem} from "@/api/assess";
    import {readNewsItem} from "@/api/assess";
    import {importantNewsItem} from "@/api/assess";
    import {saveNewsItemAggregate} from "@/api/assess";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    import { VueEditor } from 'vue2-editor';

    const toolbarOptions = [
        ['bold', 'italic', 'underline', 'strike'],        // toggled buttons
        ['blockquote', 'code-block'],

        [{ 'header': 1 }, { 'header': 2 }],               // custom button values
        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
        [{ 'script':'sub'}, { 'script': 'super' }],      // superscript/subscript
        [{ 'indent': '-1'}, { 'indent': '+1' }],          // outdent/indent
        [{ 'direction': 'rtl' }],                         // text direction

        [{ 'size': ['small', false, 'large', 'huge'] }],  // custom dropdown
        [{ 'header': [1, 2, 3, 4, 5, 6, false] }],

        [{ 'color': [] }, { 'background': [] }],          // dropdown with defaults from theme
        [{ 'font': [] }],
        [{ 'align': [] }],

        ['clean'],                                         // remove formatting button
        ['link', 'image', 'video']
    ];

    export default {
        name: "NewsItemAggregateDetail",
        props: {
            analyze_selector: Boolean,
        },
        components: {VueEditor},
        mixins: [AuthMixin],
        computed: {
            canAccess() {
                return this.checkPermission(Permissions.ASSESS_ACCESS)
            },

            canModify() {
                return this.checkPermission(Permissions.ASSESS_UPDATE)
            },

            canDelete() {
                return this.checkPermission(Permissions.ASSESS_DELETE)
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
            news_item: Object,
            title: "",
            description: "",
            toolbar: false
        }),
        methods: {
            open(news_item) {
                this.visible = true
                this.news_item = news_item;
                this.title = news_item.title;
                this.description = news_item.description;
                this.editorData = this.news_item.comments

                this.$root.$emit('first-dialog', 'push');
            },
            close() {
                this.visible = false;
                if (this.canModify) {
                    saveNewsItemAggregate(this.getGroupId(), this.news_item.id, this.title, this.description, this.editorData).then(() => {
                        this.news_item.comments = this.editorData
                        this.news_item.title = this.title
                        this.news_item.description = this.description
                    });
                }

                this.$root.$emit('first-dialog','');
            },

            fillDetail: function () {

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
                        //this.$root.$emit('new-item-position', this.news_item);
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

                    case "ungroup":
                        groupAction({
                            'group': this.getGroupId(),
                            'action': 'UNGROUP',
                            'items': [{'type': 'AGGREGATE', 'id': this.news_item.id}]
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