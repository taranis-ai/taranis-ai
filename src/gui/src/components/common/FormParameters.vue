<template>
    <div><!-- TODO: i18 -->
        <v-container v-for="(parameter, index) in sources" :key="parameter.key">

            <v-row>
                <v-text-field v-if="ui === 'text'"

                              :label="parameter.name"
                              :name="'parameter' + index"
                              type="text"
                              v-model="values[index]"
                              v-validate="'required'"
                              :data-vv-name="'parameter' + index"
                              :disabled="disabled"
                              :error-messages="errors.collect('parameter' + index)"
                />

                <v-combobox v-else-if="ui === 'combobox'"

                            :label=$t(parameter.name)
                            :items="[]"
                            item-text="name"
                />

                <v-select v-else-if="ui === 'select'"

                          :label=$t(parameter.name)
                />

                <v-textarea v-else-if="ui === 'textarea'"


                            :label=$t(parameter.name)
                            :name="parameter.name"
                />

                <v-tooltip left>
                  <template v-slot:activator="{ on, attrs }">
                    <v-icon
                      color="primary"
                      dark
                      v-bind="attrs"
                      v-on="on"
                      class="pr-2"
                    >
                      mdi-help-circle
                    </v-icon>
                  </template>
                  <span>{{ parameter.description }}</span>
                </v-tooltip>

            </v-row>
        </v-container>
    </div>
</template>

<script>
    export default {
        name: "FormParameters",
        props: {
            ui: String,
            sources: Array,
            values: Array,
            disabled: Boolean
        }
    }
</script>
