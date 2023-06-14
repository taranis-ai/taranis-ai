<template>
  <div>
    <!-- TODO: i18 -->
    <v-container v-for="(parameter, index) in sources" :key="parameter.key">
      <v-row>
        <v-text-field
          v-if="ui === 'text'"
          v-model="value[index]"
          v-validate="'required'"
          :label="parameter.name"
          :name="'parameter' + index"
          type="text"
          :data-vv-name="'parameter' + index"
          :disabled="disabled"
          :error-messages="errors.collect('parameter' + index)"
        />

        <v-combobox
          v-else-if="ui === 'combobox'"
          :label="$t(parameter.name)"
          :items="[]"
          item-title="name"
        />

        <v-select v-else-if="ui === 'select'" :label="$t(parameter.name)" />

        <v-textarea
          v-else-if="ui === 'textarea'"
          :label="$t(parameter.name)"
          :name="parameter.name"
        />

        <v-tooltip left>
          <template #activator="{ props }">
            <v-icon color="primary" dark v-bind="props" class="pr-2">
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
  name: 'FormParameters',
  props: {
    ui: {
      type: String,
      default: 'text'
    },
    sources: {
      type: Array,
      default: () => []
    },
    values: {
      type: Array,
      default: () => []
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  data: () => ({
    value: this.values
  })
}
</script>
