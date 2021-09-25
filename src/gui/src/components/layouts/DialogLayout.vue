<template>
    <v-row justify="center">
        <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
            <v-card>

                <v-toolbar dark color="primary">
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
