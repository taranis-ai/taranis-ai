<template>
    <div class="card-item" data-type="item">
        <v-row>
            <v-col v-if="multiSelectActive" cols="1">
                <v-row justify="center" align="center">
                    <v-checkbox v-if="!analyze_selector" v-model="selected" @change="selectionChanged"></v-checkbox>
                </v-row>
            </v-col>

            <v-col class="pa-0">
                <v-hover v-slot:default="{hover}" close-delay="150">
                    <v-card flat class="card mb-1" :elevation="hover ? 12 : 2"
                            @click.stop="cardItemToolbar"
                            @mouseenter.native="toolbar=true"
                            @mouseleave.native="toolbar=cardFocus"
                            :color="selectedColor"
                    >
                        <v-layout row wrap class="pa-0 pl-0 status card-assess" v-bind:class="cardStatus()">

                            <!-- Title, date -->
                            <v-row justify="center"  style="width: 100%;">
                                <v-flex class="">
                                    <v-row class="px-4 py-1 grey--text">
                                        <v-col>
                                            <div class="caption text-left">
                                                {{$t('card_item.collected')}}: <span class="font-weight-bold">{{news_item.news_item_data.collected}}</span>
                                            </div>
                                        </v-col>
                                        <v-col class="">
                                            <div class="caption text-center">
                                                {{$t('card_item.published')}}: <span class="font-weight-bold">{{news_item.news_item_data.published}}</span>
                                            </div>
                                        </v-col>
                                        <v-col>
                                            <div class="caption text-right">
                                                {{$t('card_item.source')}}: <span
                                                    class="font-weight-bold">{{news_item.news_item_data.source}}</span>
                                            </div>
                                        </v-col>
                                    </v-row>
                                </v-flex>
                            </v-row>

                            <!-- Title -->
                            <v-row justify="center" style="width: 100%;">
                                <v-card-title class="font-weight-regular py-0" style="width: inherit;">
                                    <div v-if="word_list_regex" v-html="wordCheck(news_item.news_item_data.title)"></div>
                                    <div v-else>{{news_item.news_item_data.title}}</div>
                                </v-card-title>
                            </v-row>

                            <!-- Review -->
                            <v-row justify="center" style="width: 100%;">
                                <v-flex>
                                    <v-card-text v-if="!compact_mode">
                                        <!--{{news_item.news_item_data.review}}-->
                                        <div v-if="word_list_regex" v-html="wordCheck(news_item.news_item_data.review)"></div>
                                        <div v-else>{{news_item.news_item_data.review}}</div>
                                    </v-card-text>
                                </v-flex>
                            </v-row>

                            <!-- Url -->
                            <v-row justify="center" class="pb-4" style="width: 100%;">
                                <v-flex>
                                    <v-row justify="center">
                                        <v-col>
                                            <div class="caption font-weight-bold px-4 pb-0 pt-0 info--text">
                                                <div v-if="canAccess">{{news_item.news_item_data.link}}</div>
                                                <span style="color:grey" class="ml-5"><v-icon style="color:grey" size="12">mdi-thumb-up</v-icon> {{news_item.likes}}</span>
                                                <span style="color:grey" class="ml-5"><v-icon style="color:grey" size="12">mdi-thumb-down</v-icon> {{news_item.dislikes}}</span>
                                            </div>
                                        </v-col>
                                    </v-row>
                                </v-flex>
                            </v-row>

                            <!-- Toolbar -->
                            <v-speed-dial class="newdial" v-if="!multiSelectActive && !analyze_selector"
                                          v-model="toolbar"
                                          direction="left"
                                          transition='slide-x-reverse-transition'
                                          bottom>

                                <v-item-group>
                                    <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('ungroup')" data-btn="ungroup" :title="$t('assess.tooltip.ungroup_item')">
                                        <v-icon color="accent">mdi-ungroup</v-icon>
                                    </v-btn>

                                    <v-btn v-if="canAccess" icon @click.stop="cardItemToolbar('link')" data-btn="link" :title="$t('assess.tooltip.open_source')">
                                        <a class="alink" :href="news_item.news_item_data.link" target="_blank">
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

                                </v-item-group>

                            </v-speed-dial>
                        </v-layout>

                    </v-card>
                </v-hover>
            </v-col>
        </v-row>
    </div>
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
            }
        },
        methods: {
            itemClicked(data) {
                if (this.checkPermission(Permissions.ASSESS_ACCESS) && this.news_item.access === true) {
                    this.$emit('show-item-detail', data);
                }
            },
            selectionChanged() {
                if (this.selected === true) {
                    this.$store.dispatch("select", {'type': 'ITEM', 'id': this.news_item.id, 'item': this.news_item})
                } else {
                    this.$store.dispatch("deselect", {'type': 'ITEM', 'id': this.news_item.id, 'item': this.news_item})
                }
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
            cardStatus: function () {
                if (this.news_item.important) {
                    return "important"
                } else if (this.news_item.read) {
                    return "read"
                } else {
                    return "new"
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

<style>
    #selector .card.focus {
        background-color: #caecff;
    }

    .card .obj.center {
        text-align: center;
    }

    .card.elevation-12 {
        z-index: 1;
        background-color: rgba(100, 137, 214, 0.1);
    }

    .v-speed-dial {
        position: absolute;
        right: 0;
        padding-top: 40px;
    }

    .card-assess .col {
        margin: 0;
        padding: 0;
    }

    .card .status.new {
        border-left: 4px solid #ffd556;
    }

    .card .status.read {
        border-left: 4px solid #33DD40;
    }

    .card .status.important {
        border-left: 4px solid red;
    }

    .newdial .v-speed-dial__list {
        width: 400px;
    }
</style>