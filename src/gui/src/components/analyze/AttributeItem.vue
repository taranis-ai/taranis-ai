<template>
  <div>
    <v-textarea
      v-if="attributeItem.attribute.type === 'TEXT'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
      :hint="attributeItem.description"
    />
    <v-text-field
      v-if="attributeItem.attribute.type === 'STRING'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
      :hint="attributeItem.description"
    />
    <v-checkbox
      v-if="attributeItem.attribute.type === 'BOOLEAN'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
    />
    <v-select
      v-if="attributeItem.attribute.type === 'ENUM'"
      v-model="input"
      :readonly="readOnly"
      item-title="value"
      item-value="value"
      :items="attributeItem.attribute.attribute_enums"
      :label="attributeItem.title"
    />
    <v-radio-group
      v-if="attributeItem.attribute.type === 'RADIO'"
      v-model="input"
      :disabled="readOnly"
      :label="attributeItem.title"
    >
      <v-radio
        v-for="attr_enum in attributeItem.attribute.attribute_enums"
        :key="attr_enum.id"
        :label="attr_enum.value"
        :value="attr_enum.value"
      />
    </v-radio-group>
    <code-editor
      v-if="attributeItem.attribute.type === 'RICH_TEXT'"
      v-model:content="input"
      :read-only="readOnly"
    />
    <v-radio-group
      v-if="attributeItem.attribute.type === 'TLP'"
      v-model="input"
      :disabled="readOnly"
      :label="attributeItem.title"
    >
      <v-radio
        :label="$t('attribute.tlp_white')"
        color="blue-grey"
        value="WHITE"
      />
      <v-radio :label="$t('attribute.tlp_green')" color="green" value="GREEN" />
      <v-radio
        :label="$t('attribute.tlp_amber')"
        color="orange"
        value="AMBER"
      />
      <v-radio :label="$t('attribute.tlp_red')" color="red" value="RED" />
    </v-radio-group>
    <date-picker
      v-if="attributeItem.attribute.type === 'DATE'"
      v-model:value="input"
      :placeholder="attributeItem.title"
      :disabled="readOnly"
      value-type="format"
      class="date-picker-style"
    />

    <date-picker
      v-if="attributeItem.attribute.type === 'DATE_TIME'"
      v-model:value="input"
      :placeholder="attributeItem.title"
      type="datetime"
      :disabled="readOnly"
      value-type="format"
      class="date-picker-style"
    />
    <date-picker
      v-if="attributeItem.attribute.type === 'TIME'"
      v-model:value="input"
      :placeholder="attributeItem.title"
      type="time"
      :show-second="false"
      :disabled="readOnly"
      value-type="format"
      class="date-picker-style"
    />
    <v-text-field
      v-if="attributeItem.attribute.type === 'CVE'"
      v-model="input"
      :rules="[rules.cve]"
      :readonly="readOnly"
      :label="attributeItem.title"
    />
    <v-text-field
      v-if="attributeItem.attribute.type === 'CVSS'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
      hint="Use https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator to calculate CVSS score"
      persistent-hint
    />
    <v-autocomplete
      v-if="attributeItem.attribute.type === 'CPE'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
      :items="attributeItem.attribute_enums"
    >
      <!-- TODO: Use MyAssets for Autocomplete -->
    </v-autocomplete>
    <!-- <AttributeCVSS v-if="attributeItem.attribute.type === 'CVSS'" v-model="input" /> -->
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import CodeEditor from '../common/CodeEditor.vue'

export default {
  name: 'AttributeItem',
  components: {
    CodeEditor
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
  emits: ['update:value'],
  setup(props, { emit }) {
    const rules = ref({
      cve: (val) =>
        val.match(/^$|CVE-\d{4}-\d{4,7}/)
          ? true
          : 'Input is is not a CVE reference - CVE-YYYY-NNNN[NNN]'
    })

    const input = computed({
      get: () => props.value,
      set: (newValue) => emit('update:value', newValue || '')
    })

    return {
      input,
      rules
    }
  }
}
</script>
<style>
.date-picker-style {
  padding-bottom: 15px;
}
</style>
