<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-if="modify && groups.length > 0" depressed small @click="openSelector">
            <v-icon left>mdi-plus</v-icon>
            <span>{{$t('report_item.select_remote')}}</span>
        </v-btn>

        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="dialog" news-item-selector>

            <v-card fixed>
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
                    <v-btn icon dark @click="close">
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>
                    <v-toolbar-title>{{$t('report_item.select_remote')}}</v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-btn text dark @click="add">
                        <v-icon left>mdi-plus-box</v-icon>
                        <span>{{$t('report_item.add')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-row class="cs-inside">
                    <v-col class="cs-panel">
                        <v-list-item dense v-for="link in links" :key="link.id"
                                     @click="changeGroup($event, link.id)"
                                     :class="link.id === selected_group_id ? 'active' : ''">
                            <v-list-item-content v-if="!link.separator">
                                <v-icon regular color="cx-drawer-text">{{ link.icon }}</v-icon>
                                <v-list-item-title class="cx-drawer-text--text">{{ $t(link.title) }}
                                </v-list-item-title>
                            </v-list-item-content>
                            <v-list-item-content class="separator" v-else>
                                <v-divider class="section-divider " color="white"></v-divider>
                            </v-list-item-content>
                        </v-list-item>
                    </v-col>
                    <v-col class="cs-content">
                        <ToolbarFilterAnalyze publish_selector
                                              total_count_title="analyze.total_count"
                                              @update-report-items-filter="updateFilter"
                                              ref="toolbarFilter"></ToolbarFilterAnalyze>
                        <ContentDataAnalyze publish_selector :selection="values"
                                            class="item-selector" card-item="CardAnalyze"
                                            ref="contentData"
                                            @show-remote-report-item-detail="showReportItemDetail"
                                            @new-data-loaded="newDataLoaded"/>
                    </v-col>
                </v-row>

            </v-card>
        </v-dialog>

        <v-spacer style="height:8px"></v-spacer>

        <RemoteReportItem ref="remoteReportItemDialog"/>

        <component publish_selector class="item-selector ml-4" v-bind:is="cardLayout()" v-for="value in values"
                   :card="value"
                   :key="value.id"
                   @show-remote-report-item-detail="showReportItemDetail"
                   @remove-report-item-from-selector="removeReportItemFromSelector" />
    </v-row>
</template>

<script>
    import ContentDataAnalyze from "@/components/analyze/ContentDataAnalyze";
    import ToolbarFilter from "@/components/common/ToolbarFilter";
    import CardAnalyze from "../analyze/CardAnalyze";
    import ToolbarFilterAnalyze from "@/components/analyze/ToolbarFilterAnalyze";
    import RemoteReportItem from "@/components/analyze/RemoteReportItem";
    import Permissions from "@/services/auth/permissions";
    import {getReportItemData, updateReportItem} from "@/api/analyze";

    export default {
        name: "RemoteReportItemSelector",
        components: {
            ToolbarFilterAnalyze,
            ContentDataAnalyze,
            ToolbarFilter,
            CardAnalyze,
            RemoteReportItem
        },
        props: {
            values: Array,
            modify: Boolean,
            edit: Boolean,
            report_item_id: Number,
        },
        data: () => ({
            dialog: false,
            value: "",
            groups: [],
            links: [],
            selected_group_id: ""
        }),
        computed: {
            canModify() {
                return this.edit === false || (this.checkPermission(Permissions.ANALYZE_UPDATE) && this.modify === true)
            }
        },
        methods: {
            newDataLoaded(count) {
                this.$refs.toolbarFilter.updateDataCount(count)
            },

            changeGroup(e, group_id) {
                this.selected_group_id = group_id
                this.$store.dispatch("changeCurrentReportItemGroup", group_id);
                this.$refs.contentData.updateData(false, false);
            },

            updateFilter(filter) {
                this.$refs.contentData.updateFilter(filter)
            },

            showReportItemDetail(report_item) {
                this.$refs.remoteReportItemDialog.showDetail(report_item)
            },

            removeReportItemFromSelector(report_item) {

                let data = {}
                data.delete = true
                data.remote_report_item_id = report_item.id

                if (this.edit === true) {
                    updateReportItem(this.report_item_id, data).then(() => {
                        const i = this.values.indexOf(report_item)
                        this.values.splice(i, 1)
                    })
                } else {
                    const i = this.values.indexOf(report_item)
                    this.values.splice(i, 1)
                }

                this.$emit('remote-report-items-changed', null);
            },

            cardLayout: function () {
                return "CardAnalyze";
            },

            openSelector() {
                this.$store.dispatch("multiSelectReport", true)
                this.dialog = true;
                this.$refs.contentData.updateData(false, false);
            },

            add() {
                let selection = this.$store.getters.getSelectionReport
                let added_values = []
                let data = {}
                data.add = true
                data.report_item_id = this.report_item_id
                data.remote_report_item_ids = []
                for (let i = 0; i < selection.length; i++) {

                    let found = false
                    for (let j = 0; j < this.values.length; j++) {
                        if (this.values[j].id === selection[i].item.id) {
                            found = true
                            break
                        }
                    }

                    if (found === false) {
                        added_values.push(selection[i].item)
                        data.remote_report_item_ids.push(selection[i].item.id)
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

                this.$emit('remote-report-items-changed', null);

                this.close()
            },

            close() {
                this.$store.dispatch("multiSelectReport", false)
                this.dialog = false;
            },

            report_item_updated(data_info) {
                if (this.edit === true && this.report_item_id === data_info.report_item_id) {
                    if (data_info.user_id !== this.$store.getters.getUserId) {
                        if (data_info.add !== undefined) {
                            getReportItemData(this.report_item_id, data_info).then((response) => {
                                let data = response.data
                                for (let i = 0; i < data.remote_report_items.length; i++) {
                                    this.values.push(data.remote_report_items[i])
                                }
                            })
                        } else if (data_info.delete !== undefined) {
                            for (let i = 0; i < this.values.length; i++) {
                                if (this.values[i].id === data_info.remote_report_item_id) {
                                    this.values.splice(i, 1)
                                    break
                                }
                            }
                        }

                        this.$emit('remote-report-items-changed', null);
                    }
                }
            }
        },
        mounted() {
            this.$store.dispatch('getAllReportItemGroups', {search: ''})
                .then(() => {
                    this.groups = this.$store.getters.getReportItemGroups;

                    for (let i = 0; i < this.groups.length; i++) {
                        this.links.push({
                            icon: 'mdi-arrow-down-bold-circle-outline',
                            title: this.groups[i],
                            id: this.groups[i],
                        })
                    }

                    if (this.$store.getters.getCurrentReportItemGroup === null && this.links.length > 0) {
                        this.selected_group_id = this.links[0].id
                        this.$store.dispatch("changeCurrentReportItemGroup", this.links[0].id);
                    } else {
                        this.selected_group_id = this.links[0].id = this.$store.getters.getCurrentReportItemGroup
                    }
                });

            this.$root.$on('report-item-updated', this.report_item_updated)
        },

        beforeDestroy() {
            this.$root.$off('report-item-updated', this.report_item_updated)
        }
    }
</script>