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
                    <span class="px-3" :title="$t('publish.tooltip.range.' + day.filter)">{{ $t(day.title) }}</span>
                </v-chip>
            </v-chip-group>
            <v-icon center color="grey lighten-2" class="mr-1">mdi-drag-vertical</v-icon>

            <v-spacer></v-spacer>

            <!-- SORT -->
            <v-chip-group
                active-class="success"
                color=""
                class="pr-2"
                mandatory

            >
                <v-chip small class="px-0 mr-1" @click="filterSort('DATE_DESC')"
                        :title="$t('publish.tooltip.sort.time.descending')">
                    <v-icon class="pl-2" small center>mdi-clock-outline</v-icon>
                    <v-icon class="pr-2" small center>mdi-sort-descending</v-icon>
                </v-chip>
                <v-chip small class="px-0 mr-1" @click="filterSort('DATE_ASC')"
                        :title="$t('publish.tooltip.sort.time.ascending')">
                    <v-icon class="pl-2" small center>mdi-clock-outline</v-icon>
                    <v-icon class="pr-2" small center>mdi-sort-ascending</v-icon>
                </v-chip>
            </v-chip-group>
        </v-row>

        <v-divider class="pt-2"></v-divider>
        <v-row>
            <span class="total-count-text pl-5">{{ $t(total_count_title) }}<strong>{{ totalCount }}</strong></span>
        </v-row>
    </v-container>
</template>

<script>
import AuthMixin from "../../services/auth/auth_mixin";

export default {
    name: "ToolbarFilterPublish",
    props: {
        title: String,
        dialog: String,
        total_count_title: String
    },
    computed: {
        totalCount() {
            return this.$store.getters.getProducts.total_count
        }
    },
    data: () => ({
        status: [],
        days: [
            {title: 'toolbar_filter.all', icon: 'mdi-information-outline', type: 'info', filter: 'ALL'},
            {title: 'toolbar_filter.today', icon: 'mdi-calendar-today', type: 'info', filter: 'TODAY'},
            {title: 'toolbar_filter.this_week', icon: 'mdi-calendar-range', type: 'info', filter: 'WEEK'},
            {title: 'toolbar_filter.this_month', icon: 'mdi-calendar-month', type: 'info', filter: 'MONTH'}
        ],
        filter: {
            search: "",
            range: "ALL",
            sort: "DATE_DESC"
        },
        timeout: null
    }),
    mixins: [AuthMixin],
    methods: {
        filterSort(sort) {
            this.filter.sort = sort;
            this.$root.$emit('update-products-filter', this.filter);
        },

        filterRange(range) {
            this.filter.range = range;
            this.$root.$emit('update-products-filter', this.filter);
        },

        filterSearch: function () {
            clearTimeout(this.timeout);

            let self = this;
            this.timeout = setTimeout(function () {
                self.$root.$emit('update-products-filter', self.filter);
            }, 800);
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
        /*callDialog: function (e) {
            this.$root.$emit('callDialog', e);
        },*/
        cancel() {
        },
        add() {
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

/*.toolbar-filter .row1 {
    border-bottom: 1px solid #ddd;
}*/

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