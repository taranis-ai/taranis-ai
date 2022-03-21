<template>
    <!-- TODO: i18 -->
    <v-text-field :outlined="outlined" :filled="filled"
                  v-if="ui === 'text'"
                  :label=$t(label)
                  name="name"
                  type="text"
                  v-validate="'required'"
                  data-vv-name="name"
                  :error-messages=errors.collect(error_message)
    />

    <v-combobox v-else-if="ui === 'combobox'"
                :outlined="outlined" :filled="filled"
                :label=$t(label)
                :items="items"
                item-text="name"
    />

    <v-select :outlined="outlined" :filled="filled"
              v-else-if="ui === 'select'"
              :label=$t(label)
    />

    <v-textarea :outlined="outlined" :filled="filled"
                v-else-if="ui === 'textarea'"
                :label=$t(label)
    />

</template>

<script>

export default {
  name: 'FormElement',

  props: {
    ui: null,
    label: null,
    items: Array,
    error_message: null,
    bind: null
  },

  data: () => ({
    dense: false,
    outlined: false,
    filled: false
  }),

  methods: {},

  mounted () {}
}
</script>
