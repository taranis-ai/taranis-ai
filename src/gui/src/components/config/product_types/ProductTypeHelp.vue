<template>
  <v-dialog v-model="dialog">
    <template v-slot:activator="{ on }">
    <v-btn color="primary" dark v-on="on">
      <v-icon left>{{ UI.ICON.HELP }}</v-icon>
      <span>{{ $t('product_type.help') }}</span>
    </v-btn>
    </template>
    <v-toolbar>
      <v-btn icon dark @click="dialog = false">
        <v-icon>mdi-close-circle</v-icon>
      </v-btn>
      <v-toolbar-title>{{ $t('product_type.help') }} XX</v-toolbar-title>
    </v-toolbar>
    <v-card>
      <v-card-title>
        <v-combobox
          v-model="selected_type"
          :items="report_types"
          item-text="title"
          :label="$t('product_type.choose_report_type')"
        />
      </v-card-title>

      <v-card-text>
        <div v-if="selected_type !== null">
          <v-card style="margin-bottom: 8px">
            <v-card-title>{{ $t('product_type.report_items') }}</v-card-title>
            <v-card-text>
              {{ '{' }}% for report_item in data.report_items %{{ '}' }}
            </v-card-text>
            <v-card-text
              v-for="obj in ['name', 'name_prefix', 'type']"
              :key="obj"
            >
              <span
                ><strong>
                  {{ $t('product_type.report_items_object.' + obj) }} </strong>:
                <span
                  class="product_type_help"
                  v-html="variableUsage(obj)"
                ></span
              ></span>
            </v-card-text>
            <v-card-text> {{ '{' }}% endfor %{{ '}' }} </v-card-text>
          </v-card>

          <v-card style="margin-bottom: 8px">
            <v-card-title>{{ $t('product_type.news_items') }}</v-card-title>
            <v-card-text>
              {{ '{' }}% for report_item in data.report_items %{{ '}' }}
            </v-card-text>
            <v-card-text>
              {{ '{' }}% for news_item in report_item.news_items %{{ '}' }}
            </v-card-text>
            <v-card-text
              v-for="obj in [
                'title',
                'review',
                'content',
                'author',
                'source',
                'link',
                'published',
                'collected'
              ]"
              :key="obj"
            >
              <span
                ><strong>
                  {{ $t('product_type.news_items_object.' + obj) }} </strong
                >:
                <span
                  class="product_type_help"
                  v-html="variableUsageNewsItems(obj)"
                ></span
              ></span>
            </v-card-text>
            <v-card-text> {{ '{' }}% endfor %{{ '}' }} </v-card-text>
            <v-card-text> {{ '{' }}% endfor %{{ '}' }} </v-card-text>
          </v-card>

          <v-card
            style="margin-bottom: 8px"
            v-for="attribute_group in selected_type.attribute_groups"
            :key="attribute_group.id"
          >
            <v-card-title>{{ attribute_group.title }}</v-card-title>
            <v-card-text>
              {{ '{' }}% for report_item in data.report_items %{{ '}' }}
            </v-card-text>
            <v-card-text
              v-for="attribute_item in attribute_group.attribute_group_items"
              :key="attribute_item.id"
            >
              <span
                ><strong>{{ attribute_item.title }}</strong
                >:
                <span
                  class="product_type_help"
                  v-html="attributeUsage(attribute_item)"
                ></span
              ></span>
            </v-card-text>
            <v-card-text> {{ '{' }}% endfor %{{ '}' }} </v-card-text>
          </v-card>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'ProductTypeHelp',
  emits: ['close'],
  components: {},
  data: () => ({
    selected_type: null,
    report_types: [],
    dialog: false
  }),
  computed: {},

  methods: {
    ...mapActions('config', [
      'loadReportTypesConfig'
    ]),
    ...mapGetters('config', ['getReportTypesConfig']),

    closeHelpDialog() {
      this.$emit('close')
    },

    attributeUsage(attribute_item) {
      const variable = attribute_item.title.toLowerCase().replaceAll(' ', '_')
      if (attribute_item.max_occurrence > 1) {
        return (
          '{% <span style="color: #be6d7c">for</span> entry <span style="color: #be6d7c">in</span> <span style="color: #6d9abe">report_item.attrs.' +
          variable +
          '</span> %}{{ entry | e }}{% <span style="color: #be6d7c">endfor</span> %}'
        )
      }
      return (
        '{{ <span style="color: #6d9abe">report_item.attrs.' + variable + ' | e</span> }}'
      )
    },

    variableUsage(variable) {
      return (
        '{{ <span style="color: #6d9abe">report_item.' + variable + ' | e</span> }}'
      )
    },

    variableUsageNewsItems(variable) {
      return (
        '{{ <span style="color: #6d9abe">news_item.' +
        variable +
        ' | e</span> }}'
      )
    }
  },
  mounted() {
    this.loadReportTypesConfig().then(() => {
      this.report_types = this.getReportTypesConfig().items
    })
  },
  beforeDestroy() {
    this.$emit('close')
  }
}
</script>
