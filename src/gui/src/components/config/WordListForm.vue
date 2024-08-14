<template>
  <v-container fluid class="mt-5 pt-0">
    <v-text-field
      v-if="wordlistId > 0"
      label="ID"
      density="compact"
      :disabled="true"
      :model-value="wordlistId"
    />
    <v-form
      id="config_form"
      ref="config_form"
      validate-on="input"
      fast-fail
      @submit.prevent="updatewordlist"
    >
      <v-row no-gutters>
        <v-col cols="12" class="pa-1">
          <v-text-field
            v-model="wordlist.name"
            variant="outlined"
            :label="$t('word_list.name')"
            name="name"
            :rules="[rules.required]"
          />
        </v-col>
        <v-col cols="12" class="pa-1">
          <v-textarea
            v-model="wordlist.description"
            variant="outlined"
            :label="$t('word_list.description')"
            name="description"
          />
        </v-col>
        <v-col cols="12" class="pa-1">
          <v-text-field
            v-model="wordlist.link"
            variant="outlined"
            :label="$t('word_list.link')"
            name="link"
            :rules="[rules.url]"
          />
        </v-col>

        <v-col v-for="checkbox in usage_types" :key="checkbox.label" cols="3">
          <v-checkbox
            v-model="wordlist.usage"
            variant="outlined"
            :label="checkbox.label"
            :value="checkbox.value"
            :rules="[rules.usage]"
          />
        </v-col>

        <v-col cols="12" class="pl-1">
          <v-data-table-virtual
            v-model="wordlist.entries"
            :headers="table_headers"
            :items="wordlist.entries"
            :loading="loading"
            :search="entry_search"
            height="400"
            sticky
          >
            <template #top>
              <v-card elevation="0">
                <v-card-title>
                  <v-row no-gutters>
                    <v-text-field
                      v-model="entry_search"
                      append-inner-icon="mdi-magnify"
                      density="compact"
                      label="Search"
                      variant="outlined"
                      single-line
                      class="mr-4"
                      hide-details
                    />
                    <span class="ml-4">
                      Entries: {{ wordlist.entry_count }}
                    </span>
                  </v-row>
                  <v-row v-if="wordlist.entry_count > 1000" no-gutters>
                    <v-alert dense type="warning">
                      <v-icon left>mdi-alert</v-icon>
                      <span>
                        Showing only the first 1000 entries. Export WordList to
                        see all entries.
                      </span>
                      <v-btn
                        text="Export"
                        color="primary"
                        class="ml-2"
                        @click="exportList"
                      />
                    </v-alert>
                  </v-row>
                </v-card-title>
              </v-card>
            </template>
          </v-data-table-virtual>
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-btn type="submit" block color="success" class="mt-5"> Submit </v-btn>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
import { watch, onMounted } from 'vue'
import { ref } from 'vue'
import { getDetailedWordList } from '@/api/config'
import { notifyFailure } from '@/utils/helpers'
import { createWordList, updateWordList, exportWordList } from '@/api/config'

export default {
  name: 'WordListForm',
  props: {
    wordlistId: {
      type: Number,
      default: 0
    }
  },
  emits: ['submit'],
  setup(props, { emit }) {
    const wordlist = ref({
      name: '',
      description: '',
      link: '',
      usage: [],
      entries: []
    })
    const config_form = ref(null)
    const loading = ref(false)
    const entry_search = ref('')

    const rules = {
      required: (value) => Boolean(value) || 'Required',
      url: (value) => !value || /^https?:\/\/\S+$/.test(value) || 'Invalid URL',
      usage: (value) => parse_usage(value)
    }

    const table_headers = [
      { title: 'Word', key: 'value' },
      { title: 'Description', key: 'description' }
    ]

    const usage_types = [
      { value: 'COLLECTOR_INCLUDELIST', label: 'Collector Includelist' },
      { value: 'COLLECTOR_EXCLUDELIST', label: 'Collector Excludelist' },
      { value: 'TAGGING_BOT', label: 'Tagging Bot' }
    ]

    const groupBy = [
      {
        key: 'category',
        order: 'asc'
      }
    ]

    async function updatewordlist() {
      const { valid } = await form.value.validate()
      if (!valid) {
        return
      }

      console.info(`Submitting wordlist: ${wordlist.value.name}`)

      if (props.wordlistId > 0) {
        await updateItem(wordlist.value)
      } else {
        await createItem(wordlist.value)
      }
    }

    async function createItem(item) {
      try {
        const response = await createWordList(item)
        notifySuccess(response.data.message)
        emit('submit')
      } catch (error) {
        notifyFailure(`Failed to create ${item.name}`)
      }
    }

    async function updateItem(item) {
      try {
        const response = await updateWordList(item)
        notifySuccess(response.data.message)
        emit('submit', wordlist.value)
      } catch (error) {
        notifyFailure(`Failed to update ${item.name}`)
      }
    }

    function parse_usage(usage) {
      if (
        usage.includes('COLLECTOR_INCLUDELIST') &&
        usage.includes('COLLECTOR_EXCLUDELIST')
      ) {
        return 'Includelist and Excludelist are mutually exclusive'
      }
      if (
        usage.includes('COLLECTOR_EXCLUDELIST') &&
        usage.includes('TAGGING_BOT')
      ) {
        return 'Excludelist and Tagging Bot are mutually exclusive'
      }
      return true
    }

    function exportList() {
      const queryString = 'ids=' + props.wordlistId
      exportWordList(queryString)
    }

    async function loadWordList(word_list_id) {
      loading.value = true
      try {
        const response = await getDetailedWordList(word_list_id)
        wordlist.value = response.data
      } catch (error) {
        notifyFailure(error)
      } finally {
        loading.value = false
      }
    }

    onMounted(() => {
      loadWordList(props.wordlistId)
      config_form.value.scrollIntoView({ behavior: 'smooth' })
    })

    watch(
      () => props.wordlistId,
      (w) => {
        loadWordList(w)
      }
    )

    return {
      config_form,
      wordlist,
      loading,
      entry_search,
      table_headers,
      usage_types,
      rules,
      groupBy,
      updatewordlist,
      exportList
    }
  }
}
</script>
