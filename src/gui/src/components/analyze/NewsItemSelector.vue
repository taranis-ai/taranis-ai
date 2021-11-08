<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW" data-source="news_item_selector">
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="dialog" news-item-selector>
            <v-card flat>
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000" style="position: fixed; width: 100%;">
                    <v-btn icon dark @click="close">
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>
                    <v-toolbar-title>{{$t('assess.select_news_item')}}</v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-btn text dark @click="add">
                        <v-icon left>mdi-plus-box</v-icon>
                        <span>{{$t('assess.add')}}</span>
                    </v-btn>
                </v-toolbar>
                <v-container class="pa-0 pt-12 grey darken-4" style="max-width: 96px !important; position: fixed; left: 0; top: 0; height: 100%;">
                    <v-list dense dark>
                        <v-list-item v-for="link in links" :key="link.id" @click="changeGroup($event, link.id)"
                                     class="px-0" align="center"
                                     :class="link.id === selected_group_id ? 'active' : ''">
                            <v-list-item-content class="">
                                <v-icon>{{ link.icon }}</v-icon>
                                <v-list-item-title style="white-space: unset; font-size: 0.7em;">{{ $t(link.title) }}</v-list-item-title>
                            </v-list-item-content>
                        </v-list-item>
                    </v-list>
                </v-container>

                <v-container fluid class="pa-0 pt-12 pl-8 ma-0 ml-16" style="width: calc(100% - 64px); position: sticky;">
                    <div :style="UI.STYLE.sticky_filter_toolbar">
                        <ToolbarFilterAssess analyze_selector
                                             total_count_title="assess.total_count"
                                             @update-news-items-filter="updateFilter"
                                             ref="toolbarFilter"/>
                    </div>

                    <ContentDataAssess analyze_selector :selection="values"
                                       class="item-selector"
                                       card-item="CardAssess"
                                       selfID="selector_assess_analyze"
                                       data_set="assess_news_item"
                                       ref="contentData"
                                       @new-data-loaded="newDataLoaded"/>
                </v-container>

            </v-card>
        </v-dialog>

        <v-row>
            <v-col cols="12" :class="UI.CLASS.card_offset" v-for="value in values" :key="value.id">
                <component analyze_selector compact_mode class="item-selector" v-bind:is="cardLayout()"
                           :analyze_can_modify="canModify"
                           :card="value"
                           :showToolbar="true"
                           data_set="assess_report_item"
                           @remove-item-from-selector="removeFromSelector"
                           @show-single-aggregate-detail="showSingleAggregateDetail(value)"
                           @show-aggregate-detail="showAggregateDetail(value)"
                           @show-item-detail="showItemDetail(value)"
                />
            </v-col>
        </v-row>

        <NewsItemSingleDetail ref="newsItemSingleDetail"/>
        <NewsItemDetail ref="newsItemDetail"/>
        <NewsItemAggregateDetail ref="newsItemAggregateDetail"/>
    </v-row>
</template>

<script>
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";
    import ViewLayout from "@/components/layouts/ViewLayout";
    import ContentDataAssess from "../../components/assess/ContentDataAssess";
    import ToolbarFilterAssess from "@/components/assess/ToolbarFilterAssess";
    import CardAssess from "@/components/assess/CardAssess";
    import NewsItemSingleDetail from "@/components/assess/NewsItemSingleDetail";
    import NewsItemDetail from "@/components/assess/NewsItemDetail";
    import NewsItemAggregateDetail from "@/components/assess/NewsItemAggregateDetail";
    import {getReportItemData, updateReportItem} from "@/api/analyze";

    export default {
        name: "NewsItemSelector",
        components: {
            ViewLayout,
            ContentDataAssess,
            ToolbarFilterAssess,
            CardAssess,
            NewsItemSingleDetail,
            NewsItemDetail,
            NewsItemAggregateDetail,
        },
        props: {
            values: Array,
            analyze_selector: Boolean,
            report_item_id: Number,
            edit: Boolean,
            modify: Boolean
        },
        data: () => ({
            dialog: false,
            value: "",
            groups: [],
            links: [],
            selected_group_id: ""
        }),
        mixins: [AuthMixin],
        computed: {
            canModify() {
                return this.edit === false || (this.checkPermission(Permissions.ANALYZE_UPDATE) && this.modify === true)
            }
        },
        methods: {
            cardLayout: function () {
                return "CardAssess";
            },

            changeGroup(e, group_id) {
                this.selected_group_id = group_id
                this.$store.dispatch("changeCurrentGroup", group_id);
                this.$refs.contentData.updateData(false, false);
            },

            openSelector() {
                this.selected_group_id = this.$store.getters.getCurrentGroup
                if (this.selected_group_id === '') {
                    this.selected_group_id = this.groups[0].id
                    this.$store.dispatch("changeCurrentGroup", this.selected_group_id);
                }
                this.$store.dispatch("multiSelect", true);
                this.dialog = true;
            },

            add() {
                let selection = this.$store.getters.getSelection
                let added_values = []
                let data = {}
                data.add = true
                data.report_item_id = this.report_item_id
                data.aggregate_ids = []
                for (let i = 0; i < selection.length; i++) {
                    if (selection[i].type === 'AGGREGATE') {
                        let found = false
                        for (let j = 0; j < this.values.length; j++) {
                            if (this.values[j].id === selection[i].item.id) {
                                found = true
                                break
                            }
                        }

                        if (found === false) {
                            added_values.push(selection[i].item)
                            data.aggregate_ids.push(selection[i].item.id)
                        }
                    }
                }

                if (this.edit === true) {
                    updateReportItem(this.report_item_id, data).then(() => {
                        for (let i = 0; i < added_values.length; i++) {
                            this.values.push(added_values[i])
                        }
                    })
                } else {
                    for (let i = 0; i < added_values.length; i++) {
                        this.values.push(added_values[i])
                    }
                }

                this.close()
            },

            close() {
                this.$store.dispatch("multiSelect", false)
                this.dialog = false;
            },

            newDataLoaded(count) {
                this.$refs.toolbarFilter.updateDataCount(count)
            },

            updateFilter(filter) {
                this.$refs.contentData.updateFilter(filter)
            },

            removeFromSelector(aggregate) {

                let data = {}
                data.delete = true
                data.aggregate_id = aggregate.id

                if (this.edit === true) {
                    updateReportItem(this.report_item_id, data).then(() => {
                        const i = this.values.indexOf(aggregate)
                        this.values.splice(i, 1)
                    })
                } else {
                    const i = this.values.indexOf(aggregate)
                    this.values.splice(i, 1)
                }
            },

            showSingleAggregateDetail(news_item) {
                this.$refs.newsItemSingleDetail.open(news_item)
            },

            showAggregateDetail(news_item) {
                this.$refs.newsItemAggregateDetail.open(news_item)
            },

            showItemDetail(news_item) {
                this.$refs.newsItemDetail.open(news_item)
            },

            report_item_updated(data_info) {
                if (this.edit === true && this.report_item_id === data_info.report_item_id) {
                    if (data_info.user_id !== this.$store.getters.getUserId) {
                        if (data_info.add !== undefined) {
                            getReportItemData(this.report_item_id, data_info).then((response) => {
                                let data = response.data
                                for (let i = 0; i < data.news_item_aggregates.length; i++) {
                                    this.values.push(data.news_item_aggregates[i])
                                }
                            })
                        } else if (data_info.delete !== undefined) {
                            for (let i = 0; i < this.values.length; i++) {
                                if (this.values[i].id === data_info.aggregate_id) {
                                    this.values.splice(i, 1)
                                    break
                                }
                            }
                        }
                    }
                }
            }
        },

        updated() {
            if (this.dialog === true) {
                this.$refs.contentData.updateData(false, false);
            }
        },

        mounted() {
            this.$store.dispatch('getAllOSINTSourceGroupsAssess', {search: ''})
                .then(() => {
                    this.groups = this.$store.getters.getOSINTSourceGroups.items;
                    for (let i = 0; i < this.groups.length; i++) {
                        this.links.push({
                            icon: 'mdi-folder-multiple',
                            title: this.groups[i].name,
                            id: this.groups[i].id
                        })
                    }
                });

            this.$root.$on('report-item-updated', this.report_item_updated)
        },

        beforeDestroy() {
            this.$root.$off('report-item-updated', this.report_item_updated)
        }
    }
</script>

<style>
    .row { margin: 0; }
</style>