<template>
    <v-container v-bind="UI.TOOLBAR.CONTAINER" :style="UI.STYLE.shadow">
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.LEFT">
                <div :class="UI.CLASS.toolbar_filter_title">{{$t( title )}}</div>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.MIDDLE">
                <v-text-field v-bind="UI.ELEMENT.SEARCH" v-model="filter.search"
                              :placeholder="$t('toolbar_filter.search')"
                              v-on:keyup="filterSearch" />
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.RIGHT">
                <slot name="addbutton"></slot>
            </v-col>
        </v-row>
        <v-divider></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col class="py-0">
                <!-- DAY-S -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.DAYS">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP"
                            v-for="day in days" :key="day.filter" @click="filterRange(day.filter)">
                        <div class="px-2" :title="$t('analyze.tooltip.range.' + day.filter)">{{$t(day.title)}}</div>
                    </v-chip>
                </v-chip-group>

                <v-icon v-bind="UI.TOOLBAR.ICON.CHIPS_SEPARATOR">{{ UI.ICON.SEPARATOR }}</v-icon>

                <!-- FAVORITES -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.FAVORITES">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterCompleted">
                        <v-icon v-bind="UI.TOOLBAR.ICON.FAVORITES_CHIP" :title="$t('analyze.tooltip.filter_completed')">{{ UI.ICON.COMPLETED }}</v-icon>
                    </v-chip>
                    <v-chip  v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterIncompleted">
                        <v-icon v-bind="UI.TOOLBAR.ICON.FAVORITES_CHIP" :title="$t('analyze.tooltip.filter_incomplete')">{{ UI.ICON.INCOMPLETED }}</v-icon>
                    </v-chip>
                </v-chip-group>

                <!-- SORT -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.SORT">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('DATE_DESC')" :title="$t('analyze.tooltip.sort.time.ascending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_A">{{ UI.ICON.CLOCK }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_B">{{ UI.ICON.DESC }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('DATE_ASC')" :title="$t('analyze.tooltip.sort.time.descending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_A">{{ UI.ICON.CLOCK }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_B">{{ UI.ICON.ASC }}</v-icon>
                    </v-chip>
                </v-chip-group>
            </v-col>
        </v-row>
        <v-divider v-if="showGroupToolbar"></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW" v-if="showGroupToolbar">
            <v-col v-bind="UI.TOOLBAR.COL.SELECTOR">
                <ToolbarGroupAnalyze ref="toolbarGroupAnalyze"/>
            </v-col>
        </v-row>
        <v-divider></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.INFO">
                <span>{{ $t(total_count_title) }}<strong>{{ totalCount }}</strong></span>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.RIGHT"></v-col>
        </v-row>
    </v-container>
</template>

<script>
import AuthMixin from "../../services/auth/auth_mixin";
import ToolbarGroupAnalyze from "@/components/analyze/ToolbarGroupAnalyze";

export default {
    name: "ToolbarFilterAnalyze",
    props: {
        title: String,
        dialog: String,
        total_count_title: String,
        publish_selector: Boolean,
    },
    components: {
        ToolbarGroupAnalyze
    },
    computed: {
        totalCount() {
            return this.data_count
        },

        showGroupToolbar() {
            return !this.publish_selector && this.local_reports
        }
    },
    data: () => ({
        local_reports: true,
        status: [],
        days: [
            {title: 'toolbar_filter.all', icon: 'mdi-information-outline', type: 'info', filter: 'ALL'},
            {title: 'toolbar_filter.today', icon: 'mdi-calendar-today', type: 'info', filter: 'TODAY'},
            {title: 'toolbar_filter.this_week', icon: 'mdi-calendar-range', type: 'info', filter: 'WEEK'},
            {title: 'toolbar_filter.this_month', icon: 'mdi-calendar-month', type: 'info', filter: 'MONTH'}
        ],
        data_count: 0,
        filter: {
            search: "",
            range: "ALL",
            completed: false,
            incompleted: false,
            sort: "DATE_DESC"
        },
        timeout: null
    }),
    mixins: [AuthMixin],
    methods: {
        updateDataCount(count) {
            this.data_count = count
        },

        filterCompleted() {
            this.filter.completed = !this.filter.completed;
            this.filter.incompleted = false;
            this.$emit('update-report-items-filter', this.filter);
            if (this.publish_selector === false) {
                this.$refs.toolbarGroupAnalyze.disableMultiSelect()
            }
        },

        filterIncompleted() {
            this.filter.incompleted = !this.filter.incompleted;
            this.filter.completed = false;
            this.$emit('update-report-items-filter', this.filter);
            if (this.publish_selector === false) {
                this.$refs.toolbarGroupAnalyze.disableMultiSelect()
            }
        },

        filterSort(sort) {
            this.filter.sort = sort;
            this.$emit('update-report-items-filter', this.filter);
            if (this.publish_selector === false) {
                this.$refs.toolbarGroupAnalyze.disableMultiSelect()
            }
        },

        filterRange(range) {
            this.filter.range = range;
            this.$emit('update-report-items-filter', this.filter);
            if (this.publish_selector === false) {
                this.$refs.toolbarGroupAnalyze.disableMultiSelect()
            }
        },

        filterSearch: function () {
            clearTimeout(this.timeout);

            let self = this;
            this.timeout = setTimeout(function () {
                self.$emit('update-report-items-filter', self.filter)
                if (this.publish_selector === false) {
                    this.$refs.toolbarGroupAnalyze.disableMultiSelect()
                }
            }, 300);
        },

        changeTheme() {
            this.$vuetify.theme.themes.light.primary = "#f0f";
            this.$vuetify.theme.themes.light.secondary = '#f00';
            this.$vuetify.theme.themes.light.bg = '#0f0';
            this.$vuetify.theme.themes.light.base = '#00f';
        },
        remove(item) {
            this.chips.splice(this.chips.indexOf(item), 1);
            this.chips = [...this.chips]
        },
        cancel() {
        },
        add() {
        }

    },
    mounted() {
        this.local_reports = !window.location.pathname.includes('/group/');
    },
    watch: {
        $route() {
            this.local_reports = !window.location.pathname.includes('/group/');
        }
    }
}
</script>