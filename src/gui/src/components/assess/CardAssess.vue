<template>
    <v-container v-bind="UI.CARD.CONTAINER" :data-type="this.cardType" :data-open="opened" :data-set="data_set">
        <v-row>
            <v-col v-if="multiSelectActive" :style="UI.STYLE.card_selector_zone">
                <v-row justify="center" align="center">
                    <v-checkbox v-if="!preselected" v-model="selected" @change="selectionChanged"/>
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
                                        {{ $t('card_item.collected') }}: <strong>{{ card.created }}</strong>
                                    </div>
                                </v-col>
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div v-if="singleAggregate" align="center">
                                        {{ $t('card_item.published') }}:
                                        <strong>{{ card.news_items[0].news_item_data.published }}</strong>
                                    </div>
                                </v-col>
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div v-if="singleAggregate" align="right">
                                        {{ $t('card_item.source') }}:
                                        <strong>{{ card.news_items[0].news_item_data.source }}</strong>
                                    </div>
                                </v-col>

                                <!--TITLE-->
                                <v-col v-bind="UI.CARD.COL.TITLE">
                                    <div v-if="word_list_regex" v-html="wordCheck(card.title)"></div>
                                    <div v-else>{{ card.title }}</div>
                                </v-col>

                                <!--REVIEW-->
                                <v-col v-bind="UI.CARD.COL.REVIEW">
                                    <div v-if="!compact_mode">
                                        <div v-if="word_list_regex" v-html="wordCheck(card.description)"></div>
                                        <div v-else>{{ card.description }}</div>
                                    </div>
                                </v-col>

                                <!--FOOTER-->
                                <v-row v-bind="UI.CARD.FOOTER">
                                    <v-col cols="11">
                                        <template v-if="!singleAggregate">
                                            <v-btn depressed small color="primary" data-button="aggregate"
                                                   @click.stop="openCard">
                                                <v-icon v-if="opened" left>mdi-arrow-down-drop-circle</v-icon>
                                                <v-icon v-if="!opened" left>mdi-arrow-right-drop-circle</v-icon>
                                                <span
                                                    class="subtitle-2"> {{ $t('card_item.aggregated_items') }}: {{ card.news_items.length }}</span>
                                            </v-btn>
                                        </template>
                                        <template v-else>
                                            <span  class="caption font-weight-bold px-0 mt-1 pb-0 pt-0 info--text">
                                                {{ itemLink }}
                                            </span>
                                        </template>

                                        <span class="caption font-weight-bold grey--text pl-2 pr-1">
                                            <v-icon color="grey" size="12">mdi-thumb-up</v-icon> {{ card.likes }}
                                        </span>

                                        <span class="caption font-weight-bold grey--text pl-1 pr-2">
                                            <v-icon color="grey" size="12">mdi-thumb-down</v-icon> {{ card.dislikes }}
                                        </span>

                                        <v-btn v-if="card.in_reports_count > 0" depressed x-small
                                               color="orange lighten-2">
                                            {{ $t('card_item.in_analyze') }}
                                        </v-btn>
                                    </v-col>
                                    <v-col cols="1">
                                        <!--HOVER TOOLBAR-->
                                        <div v-show="hover">
                                            <v-row v-if="!multiSelectActive && !analyze_selector"
                                                   v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar_strip_bottom">
                                                <v-col v-bind="UI.CARD.COL.TOOLS">
                                                    <v-btn v-if="singleAggregate && canAccess" icon
                                                           @click.stop="cardItemToolbar('link')"
                                                           data-btn="link" :title="$t('assess.tooltip.open_source')">
                                                        <a class="alink" :href="card.news_items[0].news_item_data.link"
                                                           target="_blank" rel="noreferer">
                                                            <v-icon color="accent">mdi-open-in-app</v-icon>
                                                        </a>
                                                    </v-btn>
                                                    <v-btn v-if="!singleAggregate && canModify" icon
                                                           @click.stop="cardItemToolbar('ungroup')"
                                                           data-btn="ungroup"
                                                           :title="$t('assess.tooltip.ungroup_news_item')">
                                                        <v-icon color="accent">mdi-ungroup</v-icon>
                                                    </v-btn>
                                                    <v-btn v-if="canCreateReport" icon @click.stop="cardItemToolbar('new')"
                                                           :title="$t('assess.tooltip.analyze_item')"
                                                           data-btn="new">
                                                        <v-icon color="accent">mdi-file-outline</v-icon>
                                                    </v-btn>
                                                    <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('read')"
                                                           data-btn="read" :title="$t('assess.tooltip.read_item')">
                                                        <v-icon :color="buttonStatus(card.read)">mdi-eye</v-icon>
                                                    </v-btn>
                                                    <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('important')"
                                                           :title="$t('assess.tooltip.important_item')"
                                                           data-btn="important">
                                                        <v-icon :color="buttonStatus(card.important)">mdi-star</v-icon>
                                                    </v-btn>
                                                    <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('like')"
                                                           data-btn="like" :title="$t('assess.tooltip.like_item')">
                                                        <v-icon :color="buttonStatus(card.me_like)">mdi-thumb-up</v-icon>
                                                    </v-btn>
                                                    <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('unlike')"
                                                           :title="$t('assess.tooltip.dislike_item')"
                                                           data-btn="unlike">
                                                        <v-icon :color="buttonStatus(card.me_dislike)">mdi-thumb-down
                                                        </v-icon>
                                                    </v-btn>
                                                    <v-btn v-if="canDelete" icon @click.stop="cardItemToolbar('delete')"
                                                           :title="$t('assess.tooltip.delete_item')"
                                                           data-btn="delete">
                                                        <v-icon color="accent">{{ UI.ICON.DELETE }}</v-icon>
                                                    </v-btn>
                                                </v-col>
                                            </v-row>
                                            <v-row v-if="analyze_selector && analyze_can_modify"
                                                   v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                                <v-col v-bind="UI.CARD.COL.TOOLS">
                                                    <v-btn icon @click.stop="cardItemToolbar('remove')">
                                                        <v-icon color="accent">mdi-minus-circle-outline</v-icon>
                                                    </v-btn>
                                                </v-col>
                                            </v-row>
                                        </div>
                                    </v-col>
                                </v-row>
                            </v-row>
                        </v-layout>
                    </v-card>
                </v-hover>
            </v-col>
        </v-row>

        <div v-if="opened" dark class="ml-16 mb-8 grey lighten-4 rounded">
            <CardAssessItem v-for="news_item in card.news_items" :key="news_item.id" :news_item="news_item"
                            :analyze_selector="analyze_selector" :compact_mode="compact_mode"
                            :word_list_regex="word_list_regex"
                            @show-item-detail="showItemDetail(news_item)"
            />
        </div>
    </v-container>
</template>

<script>
import CardAssessItem from "@/components/assess/CardAssessItem";
import {groupAction, voteNewsItemAggregate} from "@/api/assess";
import {readNewsItemAggregate} from "@/api/assess";
import {importantNewsItemAggregate} from "@/api/assess";
import {deleteNewsItemAggregate} from "@/api/assess";
import AuthMixin from "@/services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";

export default {
    name: "CardAssess",
    props: {
        card: Object,
        analyze_selector: Boolean,
        analyze_can_modify: Boolean,
        compact_mode: Boolean,
        preselected: Boolean,
        word_list_regex: String,
        aggregate_opened: Boolean,
        data_set: String
    },
    mixins: [AuthMixin],
    components: {CardAssessItem},
    data: () => ({
        toolbar: false,
        opened: false,
        selected: false
    }),
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
        selectedColor() {
            if (this.selected === true || this.preselected) {
                return "orange lighten-4"
            } else {
                return ""
            }
        },
        singleAggregate() {
            return this.card.news_items.length === 1
        },
        itemLink() {
            if (this.card.news_items.length === 1) {
                return this.card.news_items[0].news_item_data.link
            } else {
                return ""
            }
        },
        cardType() {
            if (this.singleAggregate) {
                return "single";
            } else {
                return "aggregate";
            }
        },
        cardFocus() {
            if (this.$el.querySelector(".card .layout").classList.contains('focus')) {
                return true;
            } else {
                return false;
            }
        },
        cardStatus() {
            if (this.card.important) {
                return "important"
            } else if (this.card.read) {
                return "read"
            } else {
                return "new"
            }
        },
    },
    methods: {
        showItemDetail(data) {
            this.$emit('show-item-detail', data);

            this.stateChange('SHOW_ITEM');
        },
        openCard() {
            this.opened = !this.opened;

            this.$emit('i', {'id': this.card.id, 'opened': this.opened});
            this.$emit('card-items-reindex');
            this.$root.$emit('key-remap');

        },
        selectionChanged() {
            if (this.selected === true) {
                this.$store.dispatch("select", {'type': 'AGGREGATE', 'id': this.card.id, 'item': this.card})
            } else {
                this.$store.dispatch("deselect", {'type': 'AGGREGATE', 'id': this.card.id, 'item': this.card})
            }
        },
        itemClicked(data) {
            if (this.card.news_items.length === 1) {
                this.$emit('show-single-aggregate-detail', {
                    'data': data,
                    'isSelector': this.analyze_selector,
                    'id': this.$parent.selfID
                });
            } else {
                this.$emit('show-aggregate-detail', {
                    'data': data,
                    'isSelector': this.analyze_selector,
                    'id': this.$parent.selfID
                });
            }
            this.stateChange('SHOW_ITEM');
        },

        stateChange(_state) {
            this.$root.$emit('change-state', _state);
            this.$root.$emit('check-focus', this.$el.dataset.id);
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
                    voteNewsItemAggregate(this.getGroupId(), this.card.id, 1).then(() => {
                    });
                    break;

                case "unlike":
                    voteNewsItemAggregate(this.getGroupId(), this.card.id, -1).then(() => {
                    });
                    break;

                case "link":
                    break;

                case "new":
                    //window.console.debug("CLICK NEW");
                    this.$root.$emit('new-report', [this.card]);
                    //this.stateChange('NEW_PRODUCT');
                    //this.$root.$emit('mouse-click-analyze');
                    break;

                case "remove":
                    this.$emit('remove-item-from-selector', this.card);
                    break;

                case "important":
                    importantNewsItemAggregate(this.getGroupId(), this.card.id).then(() => {
                    });
                    break;

                case "read":
                    readNewsItemAggregate(this.getGroupId(), this.card.id).then(() => {
                    });
                    break;

                case "delete":
                    deleteNewsItemAggregate(this.getGroupId(), this.card.id).then(() => {
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
                        'items': [{'type': 'AGGREGATE', 'id': this.card.id}]
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
                    this.itemClicked(this.card);
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
            let word_list = new RegExp(this.word_list_regex, "gi");

            for (let i = 0; i < message.length; i++) {
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

            return text.replace(/[&<>"']/g, function (m) {
                return map[m];
            });
        },
        multiSelectOff() {
            this.selected = false
        },
        setFocus(id) {
            if (this.$el.dataset.id == id) {
                this.toolbar = true;
                this.$el.querySelector(".card .layout").classList.add('focus');
            } else {
                this.toolbar = false;
                this.$el.querySelector(".card .layout").classList.remove('focus');
            }
        }
    },
    created() {
        this.opened = this.aggregate_opened;
    },
    mounted() {
        this.$root.$on('multi-select-off', this.multiSelectOff);

        this.$root.$on('check-focus', (id) => {
            this.setFocus(id);
        });
    },
    beforeDestroy() {
        this.$root.$off('multi-select-off', this.multiSelectOff);
        this.$root.$off('check-focus');
    }
}
</script>