<template>
    <v-row justify="center" class="attribute-item-layout pt-2">
        <v-row no-gutters>
            <slot name="header">
                <v-row justify="center">
                    <!-- SORT -->
                    <v-chip-group
                            v-if="values.length > 1"
                            active-class="success"
                            color=""
                            class="pr-4"
                            mandatory

                    >
                        <v-chip small class="px-0 mr-1" :title="$t('report_item.tooltip.sort_time')">
                            <v-icon class="px-2" small center @click="sort(false)">mdi-clock-outline</v-icon>
                        </v-chip>
                        <v-chip small class="px-0 mr-1" :title="$t('report_item.tooltip.sort_user')">
                            <v-icon class="px-2" small center @click="sort(true, $store.getters.getUserName)">mdi-account</v-icon>
                        </v-chip>
                    </v-chip-group>
                </v-row>
            </slot>
        </v-row>
        <v-row class="ml-0 mr-4">
            <slot name="content"></slot>
        </v-row>
        <v-row class="ml-3 mr-5">
            <slot name="footer" class="pr-0">
                <v-btn v-if="add_button" depressed small block class="mt-2 " @click="add" :title="$t('report_item.tooltip.add_value')">
                    <v-icon center>mdi-plus</v-icon>
                </v-btn>
            </slot>
        </v-row>
    </v-row>
</template>

<script>
export default {
    name: "AttributeItemLayout",
    props: {
        add_button: null,
        values: Array
    },
    methods: {
        add() {
            this.$emit('add-value');
        },

        sort(my_first, user_name) {
            this.values.sort(function (a, b) {

                if (my_first) {
                    if (user_name === a.user.name && user_name !== b.user.name) {
                        return 1
                    } else if (user_name !== a.user.name && user_name === b.user.name) {
                        return -1
                    }
                }

                if (a.last_updated < b.last_updated) {
                    return -1
                } else if (a.last_updated > b.last_updated) {
                    return 1
                } else {
                    return 1
                }
            });
        }
    }
}
</script>

<style>
.attribute-item-layout .row {
    width: 100%;
}
</style>