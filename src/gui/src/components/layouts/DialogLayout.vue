<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
            <v-card>

                <v-toolbar v-bind="UI.DIALOG.TOOLBAR">
                    <!-- BUTTON CANCEL -->
                    <v-btn icon dark @click="visible = false">
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>
                    <v-toolbar-title>{{ title }}</v-toolbar-title>
                    <v-spacer></v-spacer>

                    <!-- BUTTON ADD -->
                    <v-btn text>
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('osint_source.add')}}</span>
                    </v-btn>
                </v-toolbar>
                <v-container fluid class="content">
                    <slot name="content"></slot>
                </v-container>

            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
    export default {
        name: "DialogLayout"
    }
</script>