<template>
    <v-toolbar dense dark floating absolute short width="100%">
        <v-toolbar-items>

            <v-select
                    :items="sort"
                    :menu-props="{ offsetY: true }"
                    :label="$t('analyze.sort')"
            ></v-select>

            <DateInput :caption="$t('analyze.from')"></DateInput>
            <DateInput :caption="$t('analyze.to')"></DateInput>

            <div class="toolbar-buttons-right mt-1 mr-2">

                <v-btn icon small>
                    <v-icon small>mdi-magnify</v-icon>
                </v-btn>

                <v-btn icon small>
                    <v-icon small>mdi-checkbox-multiple-marked</v-icon>
                </v-btn>

                <v-btn icon small>
                    <v-icon small>mdi-dots-vertical</v-icon>
                </v-btn>

            </div>
        </v-toolbar-items>
    </v-toolbar>
</template>

<script>
    import DateInput from "../../components/common/DateInput";

    export default {
        name: "AnalyzeFilter",
        components: {DateInput},
        data: () => ({
            sort: ['Latest', 'Oldest', 'Most relevant'],
            dateFrom: null,
            menuFrom: false,
        }),
    }
</script>