<template>
    <v-container fluid class="toolbar-filter ma-0 pa-0 pb-2 cx-toolbar-filter primary">

        <!-- Heading -->
        <v-row class="row1">
            <span class="display-1 primary--text ma-1 pl-4 view-heading">{{ $t(title) }}</span>
            <v-spacer></v-spacer>

            <v-text-field class="search"
                          :placeholder="$t('toolbar_filter.search')"
                          prepend-inner-icon='mdi-card-search'
                          dense
                          v-on:keyup="filterSearch"
                          v-model="filter.search"
            ></v-text-field>

            <v-spacer></v-spacer>
            <!-- ADD NEW BUTTON -->
            <slot name="addbutton"></slot>
        </v-row>
        <v-divider></v-divider>

        <!-- Chips • USER -->
        <v-row class="user ml-5 mt-0">
            <!-- DAY-S -->
            <v-chip-group
                active-class="info"
                color="primary"
                mandatory
            >
                <v-chip v-for="day in days" :key="day.filter" small class="px-0 mr-1" @click="filterRange(day.filter)">
                    <span class="px-3" :title="$t('analyze.tooltip.range.' + day.filter)">{{ $t(day.title) }}</span>
                </v-chip>
            </v-chip-group>
            <v-icon center color="grey lighten-2" class="mr-1">mdi-drag-vertical</v-icon>

            <!-- FAVORITES -->
            <v-chip-group
                active-class="info"
                color=""
                class="pr-4"
            >
                <v-chip small class="px-0 mr-1" @click="filterCompleted"
                        :title="$t('analyze.tooltip.filter_completed')">
                    <v-icon small center class="px-2">mdi-progress-check</v-icon>
                </v-chip>
                <v-chip small class="px-0 mr-1" @click="filterIncompleted"
                        :title="$t('analyze.tooltip.filter_incomplete')">
                    <v-icon small center class="px-2">mdi-progress-close</v-icon>
                </v-chip>
            </v-chip-group>

            <v-spacer></v-spacer>

            <!-- SORT -->
            <v-chip-group
                active-class="success"
                color=""
                class="pr-4"
                mandatory

            >
                <v-chip small class="px-0 mr-1" @click="filterSort('DATE_DESC')"
                        :title="$t('analyze.tooltip.sort.time.ascending')">
                    <v-icon class="pl-2" small center>mdi-clock-outline</v-icon>
                    <v-icon class="pr-2" small center>mdi-sort-descending</v-icon>
                </v-chip>
                <v-chip small class="px-0 mr-1" @click="filterSort('DATE_ASC')"
                        :title="$t('analyze.tooltip.sort.time.descending')">
                    <v-icon class="pl-2" small center>mdi-clock-outline</v-icon>
                    <v-icon class="pr-2" small center>mdi-sort-ascending</v-icon>
                </v-chip>
            </v-chip-group>
        </v-row>

        <v-divider v-if="showGroupToolbar"></v-divider>
        <v-row v-if="showGroupToolbar">
            <ToolbarGroupAnalyze ref="toolbarGroupAnalyze"/>
        </v-row>
        <v-divider class="pt-2"></v-divider>
        <v-row>
            <span class="total-count-text mx-5">{{ $t(total_count_title) }}<strong>{{ totalCount }}</strong></span>
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

<style>
.toolbar-filter {
    box-shadow: 0px 1px 5px rgba(0, 0, 0, 0.4);
}

#app:not(.theme--dark) .toolbar-filter {
    box-shadow: 0px 1px 5px rgba(0, 0, 0, 0.15);
}

.toolbar-filter .row1 .view-heading {
    text-transform: uppercase;
    font-weight: 300;
}

.toolbar-filter .custom-filter {
    height: 32px;
}

.toolbar-filter .custom-filter .v-input__control {
    min-height: 32px;
}

.toolbar-filter .custom-filter .v-input__control .v-input__slot {
    padding: 0;
    padding-left: 0.1em;
}

.toolbar-filter .custom-filter .v-select__selections {
    min-height: 32px;
}

.toolbar-filter .custom-filter .filter-tag {
    height: 22px;
}

.toolbar-filter .custom-filter [placeholder]::placeholder {
    font-size: 0.8em;
    padding-left: 1em;
}

.toolbar-filter .admin .v-chip.v-chip--active,
.toolbar-filter .user .v-chip.v-chip--active {
    opacity: 1;
}

.toolbar-filter .admin .v-chip:not(.v-chip--active),
.toolbar-filter .user .v-chip:not(.v-chip--active) {
    opacity: 0.5;
}

.toolbar-filter .v-chip:not(.v-chip--active):hover {
    opacity: 1;
}

.search {
    padding-top: 0;
    padding-left: 8px;
    padding-right: 8px;
    margin-top: 8px;
    height: 32px;
    background-color: #f8f8f8;
    border-radius: 4px;
}

.v-chip-group .v-slide-group__content {
    padding-top: 0 !important;
}

.v-chip-group .v-chip.filter {
    height: 20px;
    margin-top: 5px;
}

</style>