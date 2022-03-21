<template>
    <div>
        <!-- TODO: i18 :label-->
        <v-text-field
                :label="parameter.name"
                name="value"
                type="text"
                v-model="value"
                v-validate="'required'"
                data-vv-name="value"
                :error-messages="errors.collect('value')"
        ></v-text-field>
    </div>
</template>

<script>
export default {
  name: 'Parameter',
  props: ['parameter'],
  data: () => ({
    value: ''
  })
}
</script>
