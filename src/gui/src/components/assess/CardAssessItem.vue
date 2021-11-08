<template>
    <v-container v-bind="UI.CARD.CONTAINER" data-type="item">
        <v-row>
            <v-col v-if="multiSelectActive" :style="UI.STYLE.card_selector_zone">
                <v-row justify="center" align="center">
                    <v-checkbox v-if="!analyze_selector" v-model="selected" @change="selectionChanged"></v-checkbox>
                </v-row>
            </v-col>

            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{hover}">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2"
                            @click.stop="cardItemToolbar"
                            @mouseenter.native="toolbar=true"
                            @mouseleave.native="toolbar=cardFocus"
                            :color="selectedColor"
                    >
                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" :class="'status ' + cardStatus">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <!--COLLECTED, PUBLISHED, SOURCE-->
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div>
                                        {{ $t('card_item.collected') }}: <strong>{{ news_item.news_item_data.collected }}</strong>
                                    </div>
                                </v-col>
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div align="center">
                                        {{ $t('card_item.published') }}:
                                        <strong>{{ news_item.news_item_data.published }}</strong>
                                    </div>
                                </v-col>
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div align="right">
                                        {{ $t('card_item.source') }}:
                                        <strong>{{ news_item.news_item_data.source }}</strong>
                                    </div>
                                </v-col>

                                <!--TITLE-->
                                <v-col v-bind="UI.CARD.COL.TITLE">
                                    <div v-if="word_list_regex" v-html="wordCheck(news_item.news_item_data.title)"></div>
                                    <div v-else>{{ news_item.news_item_data.title }}</div>
                                </v-col>

                                <!--REVIEW-->
                                <v-col v-bind="UI.CARD.COL.REVIEW">
                                    <div v-if="!compact_mode">
                                        <div v-if="word_list_regex" v-html="wordCheck(news_item.news_item_data.review)"></div>
                                        <div v-else>{{ news_item.news_item_data.review }}</div>
                                    </div>
                                </v-col>

                                <!--FOOTER-->
                                <v-row v-bind="UI.CARD.FOOTER">
                                    <v-col cols="11">
                                        <span v-if="canAccess" class="caption font-weight-bold px-0 mt-1 pb-0 pt-0 info--text">
                                            {{ news_item.news_item_data.link }}
                                        </span>

                                        <span class="caption font-weight-bold grey--text pl-2 pr-1">
                                            <v-icon color="grey" size="12">mdi-thumb-up</v-icon> {{ news_item.likes }}
                                        </span>

                                        <span class="caption font-weight-bold grey--text pl-1 pr-2">
                                            <v-icon color="grey" size="12">mdi-thumb-down</v-icon> {{ news_item.dislikes }}
                                        </span>
                                    </v-col>

                                    <!--HOVER TOOLBAR-->
                                    <v-col cols="1">
                                        <v-row v-if="!multiSelectActive && !analyze_selector && hover"
                                               :style="UI.STYLE.card_toolbar">
                                            <v-col v-bind="UI.CARD.COL.TOOLS" :style="UI.STYLE.card_toolbar_strip_bottom">
                                                <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('ungroup')" data-btn="ungroup" :title="$t('assess.tooltip.ungroup_item')">
                                                    <v-icon color="accent">mdi-ungroup</v-icon>
                                                </v-btn>

                                                <v-btn v-if="canAccess" icon @click.stop="cardItemToolbar('link')" data-btn="link" :title="$t('assess.tooltip.open_source')">
                                                    <a class="alink" :href="news_item.news_item_data.link" target="_blank" rel="noreferer">
                                                        <v-icon color="accent">mdi-open-in-app</v-icon>
                                                    </a>
                                                </v-btn>

                                                <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('read')" data-btn="read" :title="$t('assess.tooltip.read_item')">
                                                    <v-icon :color="buttonStatus(news_item.read)">mdi-eye</v-icon>
                                                </v-btn>

                                                <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('important')" data-btn="important" :title="$t('assess.tooltip.important_item')">
                                                    <v-icon :color="buttonStatus(news_item.important)">mdi-star</v-icon>
                                                </v-btn>

                                                <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('like')" data-btn="like" :title="$t('assess.tooltip.like_item')">
                                                    <v-icon :color="buttonStatus(news_item.me_like)">mdi-thumb-up</v-icon>
                                                </v-btn>

                                                <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('unlike')" data-btn="unlike" :title="$t('assess.tooltip.dislike_item')">
                                                    <v-icon :color="buttonStatus(news_item.me_dislike)">mdi-thumb-down</v-icon>
                                                </v-btn>

                                                <v-btn v-if="canDelete" icon @click.stop="cardItemToolbar('delete')" data-btn="delete" :title="$t('assess.tooltip.delete_item')">
                                                    <v-icon color="accent">mdi-delete</v-icon>
                                                </v-btn>

                                            </v-col>
                                        </v-row>
                                    </v-col>
                                </v-row>
                            </v-row>
                        </v-layout>
                    </v-card>
                </v-hover>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
    import {groupAction, voteNewsItem} from "@/api/assess";
    import {readNewsItem} from "@/api/assess";
    import {importantNewsItem} from "@/api/assess";
    import {deleteNewsItem} from "@/api/assess";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "CardAssessItem",
        props: {
            news_item: Object,
            analyze_selector: Boolean,
            compact_mode: Boolean,
            word_list_regex: String
        },
        mixins: [AuthMixin],
        data: () => ({
            toolbar: false,
            selected: false
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
            selectedColor() {
                if (this.selected === true) {
                    return "orange lighten-4"
                } else {
                    return ""
                }
            },
            cardFocus() {
                if(this.$el.querySelector(".card .layout").classList.contains('focus')) {
                    return true;
                } else {
                    return false;
                }
            },
            cardStatus() {
                if (this.news_item.important) {
                    return "important"
                } else if (this.news_item.read) {
                    return "read"
                } else {
                    return "new"
                }
            },
        },
        methods: {
            itemClicked(data) {
                if (this.checkPermission(Permissions.ASSESS_ACCESS) && this.news_item.access === true) {
                    this.$emit('show-item-detail', data);
                    this.stateChange();
                }
            },
            selectionChanged() {
                if (this.selected === true) {
                    this.$store.dispatch("select", {'type': 'ITEM', 'id': this.news_item.id, 'item': this.news_item})
                } else {
                    this.$store.dispatch("deselect", {'type': 'ITEM', 'id': this.news_item.id, 'item': this.news_item})
                }
            },
            stateChange() {
                this.$root.$emit('change-state','SHOW_ITEM');
                this.$root.$emit('check-focus',this.$el.dataset.id);
                this.$root.$emit('update-pos', parseInt(this.$el.dataset.id));
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
                        });
                        break;

                    case "unlike":
                        voteNewsItem(this.getGroupId(), this.news_item.id, -1).then(() => {
                        });
                        break;

                    case "link":
                        break;

                    case "important":
                        importantNewsItem(this.getGroupId(), this.news_item.id).then(() => {
                        });
                        break;

                    case "read":
                        readNewsItem(this.getGroupId(), this.news_item.id).then(() => {
                        });
                        break;

                    case "delete":
                        deleteNewsItem(this.getGroupId(), this.news_item.id).then(() => {
                        }).catch((error) => {
                            this.$root.$emit('notification',
                                {
                                    type: 'error',
                                    loc: 'error.' + error.response.data
                                }
                            )
                        });
                        break;

                    case "ungroup":
                        groupAction({
                            'group': this.getGroupId(),
                            'action': 'UNGROUP',
                            'items': [{'type': 'ITEM', 'id': this.news_item.id}]
                        }).then(() => {
                        }).catch((error) => {
                            this.$root.$emit('notification',
                                {
                                    type: 'error',
                                    loc: 'error.' + error.response.data
                                }
                            )
                        });
                        break;

                    default:
                        this.toolbar = false;
                        this.itemClicked(this.news_item);
                        break;
                }
            },

            buttonStatus: function (active) {
                if (active) {
                    return "info"
                } else {
                    return "accent"
                }
            },
            wordCheck(target) {
                let parse = new Array();
                let message = this.escapeHtml(target).split(' ');
                let word_list = new RegExp(this.word_list_regex,"gi");

                for( let i=0; i<message.length; i++ ) {
                    let res = message[i].replace(word_list, function (x) {
                        return "<span class='wordlist'>" + x + "</span>";
                    });

                    parse.push(res + " ");
                }

                return parse.join('');
            },
            escapeHtml(text) {
                let map = {
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#039;'
                };

                return text.replace(/[&<>"']/g, function(m) { return map[m]; });
            },
            multiSelectOff() {
                this.selected = false
            },
            setFocus(id) {
                if(this.$el.dataset.id == id) {
                    this.toolbar = true;
                    this.$el.querySelector(".card .layout").classList.add('focus');
                } else {
                    this.toolbar = false;
                    this.$el.querySelector(".card .layout").classList.remove('focus');
                }
            }
        },
        mounted() {
            this.$root.$on('multi-select-off', this.multiSelectOff);

            this.$root.$on('check-focus', (id) => {
                this.setFocus(id);
            });
        },
        beforeDestroy() {
            this.$root.$off('multi-select-off', this.multiSelectOff);
        }
    }
</script>