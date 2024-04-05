<template>
  <div>
    <v-textarea
      v-if="attributeItem.type === 'TEXT'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
      :hint="attributeItem.description"
    />
    <v-text-field
      v-if="attributeItem.type === 'STRING'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
      :hint="attributeItem.description"
    />
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
      :items="attributeItem.render_data.attribute_enums"
      :label="attributeItem.title"
    />
    <v-radio-group
      v-if="attributeItem.type === 'RADIO'"
      v-model="input"
      :disabled="readOnly"
      :label="attributeItem.title"
    >
      <v-radio
        v-for="attr_enum in attributeItem.render_data.attribute_enums"
        :key="attr_enum.id"
        :label="attr_enum.value"
        :value="attr_enum.value"
      />
    </v-radio-group>
    <code-editor
      v-if="attributeItem.type === 'RICH_TEXT'"
      v-model:content="input"
      :read-only="readOnly"
    />
    <AttributeTLP
      v-if="attributeItem.type === 'TLP'"
      v-model="input"
      :read-only="readOnly"
      :title="attributeItem.title"
    />
    <VueDatePicker
      v-if="
        attributeItem.type === 'DATE' ||
        attributeItem.type === 'DATE_TIME' ||
        attributeItem.type === 'TIME'
      "
      v-model="input"
      class="mb-5"
      :name="'dateAttribute-' + attributeItem.title"
      :placeholder="attributeItem.title"
      :readonly="readOnly"
      position="left"
      :time-picker-inline="
        attributeItem.type === 'TIME' || attributeItem.type === 'DATE_TIME'
      "
      clearable
      auto-apply
    />
    <v-text-field
      v-if="attributeItem.type === 'CVE'"
      v-model="input"
      :rules="[rules.cve]"
      :readonly="readOnly"
      :label="attributeItem.title"
    />
    <v-text-field
      v-if="attributeItem.type === 'CVSS'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
      persistent-hint
    />
    <div v-if="attributeItem.type === 'CVSS'" class="hint-text">
      Use
      <a
        href="https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator"
        target="_blank"
        >https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator</a
      >
      to calculate CVSS score
    </div>
    <v-autocomplete
      v-if="attributeItem.type === 'CPE'"
      v-model="input"
      :readonly="readOnly"
      :label="attributeItem.title"
      :items="attributeItem.attribute_enums"
    >
      <!-- TODO: Use MyAssets for Autocomplete -->
    </v-autocomplete>
    <AttributeStory
      v-if="attributeItem.type === 'STORY'"
      v-model="input"
      :readonly="readOnly"
      :title="attributeItem.title"
    />
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import CodeEditor from '../common/CodeEditor.vue'
import AttributeTLP from './AttributeTLP.vue'
import AttributeStory from './AttributeStory.vue'

export default {
  name: 'AttributeItem',
  components: {
    CodeEditor,
    AttributeTLP,
    AttributeStory
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
.hint-text {
  color: #888;
  font-size: 0.85rem;
  margin-bottom: 15px;
}
</style>
