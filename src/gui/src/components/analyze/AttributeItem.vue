<template>
  <div>
    <v-textarea
      v-if="attributeItem.type === 'TEXT'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
    ></v-textarea>
    <v-text-field
      v-if="attributeItem.type === 'STRING'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
    ></v-text-field>
    <v-checkbox
      v-if="attributeItem.type === 'BOOLEAN'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
    />
    <v-select
      v-if="attributeItem.type === 'ENUM'"
      v-model="input"
      :readonly="readOnly"
      item-title="value"
      item-value="value"
      :items="attributeItem.attribute_enums"
      :label="attributeItem.title"
    />
    <v-radio-group
      v-if="attributeItem.type === 'RADIO'"
      v-model="input"
      :disabled="readOnly"
      row
    >
      <v-radio
        v-for="attr_enum in attributeItem.attribute_enums"
        :key="attr_enum.id"
        :label="attr_enum.value"
        :value="attr_enum.value"
      ></v-radio>
    </v-radio-group>
    <!-- <vue-editor
      v-if="attributeItem.type === 'RICH_TEXT'"
      v-model="input"
      :disabled="readOnly"
      :editor-options="{
        height: 300
      }"
    /> -->
    <v-radio-group
      v-if="attributeItem.type === 'TLP'"
      v-model="input"
      :disabled="readOnly"
      row
      :label="attributeItem.title"
    >
      <v-radio
        :label="$t('attribute.tlp_white')"
        color="blue-grey-lighten-4"
        value="WHITE"
      ></v-radio>
      <v-radio
        :label="$t('attribute.tlp_green')"
        color="green"
        value="GREEN"
      ></v-radio>
      <v-radio
        :label="$t('attribute.tlp_amber')"
        color="orange"
        value="AMBER"
      ></v-radio>
      <v-radio
        :label="$t('attribute.tlp_red')"
        color="red"
        value="RED"
      ></v-radio>
    </v-radio-group>
    <date-picker
      v-if="attributeItem.type === 'DATE'"
      v-model:value="input"
      :placeholder="attributeItem.title"
      :disabled="readOnly"
      value-type="format"
      class="date-picker-style"
    />

    <date-picker
      v-if="attributeItem.type === 'DATE_TIME'"
      v-model:value="input"
      :placeholder="attributeItem.title"
      type="datetime"
      :disabled="readOnly"
      value-type="format"
      class="date-picker-style"
    />
    <date-picker
      v-if="attributeItem.type === 'TIME'"
      v-model:value="input"
      :placeholder="attributeItem.title"
      type="time"
      :show-second="false"
      :disabled="readOnly"
      value-type="format"
      class="date-picker-style"
    />
    <v-text-field
      v-if="attributeItem.type === 'CVE'"
      v-model="input"
      :rules="[rules.cve]"
      :readonly="readOnly"
      :label="attributeItem.title"
    >
    </v-text-field>
    <v-autocomplete
      v-if="attributeItem.type === 'CPE'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
      :items="attributeItem.attribute_enums"
    >
      <!-- TODO: Use MyAssets for Autocomplete -->
    </v-autocomplete>
    <!-- <AttributeCVSS v-if="attributeItem.type === 'CVSS'" v-model="input" /> -->
  </div>
</template>

// ATTACHMENT: 'Attachment'

<script>
// import AttributeCVSS from './AttributeCVSS.vue'

export default {
  name: 'AttributeItem',
  components: {
    // AttributeCVSS
  },
  props: {
    value: {
      type: String,
      default: '',
      required: true
    },
    attributeItem: {
      type: Object,
      required: true
    },
    readOnly: { type: Boolean, default: false }
  },
  emits: ['input'],
  data: () => ({
    rules: {
      cve: (value) =>
        value.match(/^$|CVE-\d{4}-\d{4,7}/)
          ? true
          : 'Input is is not a CVE reference'
    }
  }),
  computed: {
    input: {
      get() {
        return this.value
      },
      set(value) {
        this.$emit('input', value || '')
      }
    }
  }
}
</script>
<style>
.date-picker-style {
  padding-bottom: 15px;
}
</style>
