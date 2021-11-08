<template>
    <v-tooltip bottom :content-class="hideTooltip">
        <template v-slot:activator="{on}">
            <v-btn v-on="on">
                <v-icon v-if="showIconLeft" left>{{icon_left}}</v-icon>
                {{label}}
                <v-icon v-if="showIconRight" right>{{icon_right}}</v-icon>
            </v-btn>
        </template>
        <span>{{ $t(tooltip) }}</span>
    </v-tooltip>
</template>

<script>
    export default {
        name: "CSButton",
        props: {
            label: String,
            tooltip: String,
            show: Boolean,
            icon_left: String,
            icon_right: String
        },
        data: () => ({
        }),
        computed: {
            hideTooltip() {
                return !this.show ? "hide-tooltip" : "";
            },
            showIconLeft() {
                return this.icon_left;
            },
            showIconRight() {
                return this.icon_right;
            }
        }
    }
</script>