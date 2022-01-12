<template>
    <v-container class="pa-0">
      <v-row>
        <v-col class="pa-5 pb-3">

          <!-- search -->

          <v-row class="pl-5 pr-5 pt-5">
            <v-col>
              <h4>search</h4>
            </v-col>
          </v-row>
          <v-row class="pl-5 pr-5">
            <v-col>
              <v-text-field label="search" outlined dense append-icon="$awakeSearch"></v-text-field>
            </v-col>
          </v-row>

        </v-col>
      </v-row>

          <v-divider class="mt-0 mb-0"></v-divider>
        
      <v-row>
        <v-col class="pa-5 pb-3">

          <!-- filter results -->
          
          <v-row class="pl-5 pr-5 pt-4">
            <v-col>
              <h4>filter results</h4>
            </v-col>
          </v-row>

          <!-- time tags -->
          <v-row class="pl-5 pr-5">
            <v-col justify="space-between" class="d-flex pb-0" style="column-gap: 10px;">
              <v-btn outlined :class="['text-lowercase', 'filter-btn', {'clicked': date.chips.all,}]" @click="dateSelector('all')"> all </v-btn>
              <v-btn outlined :class="['text-lowercase', 'filter-btn', {'clicked': date.chips.today,}]" @click="dateSelector('today')"> today </v-btn>
              <v-btn outlined :class="['text-lowercase', 'filter-btn', {'clicked': date.chips.week,}]" @click="dateSelector('week')"> this week </v-btn>
            </v-col>
          </v-row>

          <!-- date picker -->
          <v-row class="pl-5 pr-5 mt-2 mb-0">
            <v-col>
              <v-menu
                ref="datePicker"
                v-model="datePicker"
                :close-on-content-click="false"
                :return-value.sync="date"
                transition="scale-transition"
                offset-y
                min-width="auto"
              >
                <template v-slot:activator="{ on, attrs }">
                  <v-text-field readonly outlined dense append-icon="mdi-calendar-range-outline"
                    v-model="dateRangeText"
                    v-bind="attrs"
                    v-on="on"
                    placeholder="Date range"
                    hide-details
                    :class="[{'text-field-active': (date.range).length,}]"
                  ></v-text-field>
                </template>
                <v-date-picker
                  v-model="date.range"
                  range
                  no-title
                  scrollable
                >
                  <v-spacer></v-spacer>
                  <v-btn text color="primary" @click="datePicker = false">
                    Cancel
                  </v-btn>
                  <v-btn text color="primary" @click="$refs.datePicker.save(date), dateSelector('range')">
                    OK
                  </v-btn>
                </v-date-picker>
              </v-menu>
            </v-col>
          </v-row>

          <!-- tags -->
          <v-row class="pl-5 pr-5 mt-1 mb-5">
            <v-col>
              <v-combobox
              v-model="tags.selected"
              :items="tags.list"
              label="tags"
              multiple
              outlined 
              dense
              append-icon="mdi-chevron-down"
              class="pl-0"
              hide-details
              deletable-chips
              @focus="focused=true"
              @blur="focused=false"
            >
              <template v-slot:selection="{ item, index }">
                <v-chip small v-if="index < 1 && !focused" @click:close="deleteChip(item)" label color="grey--lighten-4"
                close close-icon="mdi-close" class="pa-2 ml-0 mt-1">
                  <span>{{ item }}</span>
                </v-chip>
                <v-chip small v-else-if="focused" @click:close="deleteChip(item)" label color="grey--lighten-4"
                close close-icon="mdi-close" class="pa-2 ml-0 mt-1">
                  <span>{{ item }}</span>
                </v-chip>

                <span
                  v-if="index === 1 && !focused"
                  class="grey--text text-caption"
                >
                  (+{{ tags.selected.length - 1 }})
                </span>
              </template>
            </v-combobox>
            </v-col>
          </v-row>

        </v-col>
      </v-row>

          <v-divider class="mt-0 mb-0"></v-divider>
        
      <v-row>
        <v-col class="pa-5 pb-3">

          <v-row class="pl-5 pr-5 pt-4">
            <v-col class="pb-0">
              <h4>only show</h4>
            </v-col>
          </v-row>

          <v-row>
            <v-col class="pb-5">
              <v-list dense>
                <v-list-item-group
                  v-model="filterBy.selected"
                  active-class="selected"
                  multiple
                  class="filter-list"
                >
                  <template v-for="item in filterBy.list">
                    <v-list-item :key="item.title" class="extra-dense" :ripple="false">
                      <template v-slot:default="{ active }">
                        
                        <v-list-item-icon class="mr-2">
                          <v-icon v-if="!active" small color="grey" class="filter-icon mt-auto mb-auto">
                            {{ item.icon }}
                          </v-icon>
                          <v-icon v-else small color="primary" class="filter-icon-active mt-auto mb-auto">
                            {{ item.icon }}
                          </v-icon>
                        </v-list-item-icon>

                        <v-list-item-content class="py-1 mt-auto mb-auto">
                          {{ item.label }}
                        </v-list-item-content>

                        <v-list-item-action>
                          <v-icon v-if="active" small color="dark-grey" class="mt-auto mb-auto">
                            mdi-check
                          </v-icon>
                        </v-list-item-action>
                      </template>
                    </v-list-item>
                  </template>
                </v-list-item-group>
              </v-list>
            </v-col>
          </v-row>

        </v-col>
      </v-row>

          <v-divider class="mt-2 mb-0"></v-divider>
        
      <v-row>
        <v-col class="pa-5 pb-3">

          <v-row class="pl-5 pr-5 pt-4">
            <v-col class="pb-0">
              <h4>sort by</h4>
            </v-col>
          </v-row>

          <v-row>
            <v-col class="pb-5">
              <v-list dense>
                <v-list-item-group
                  v-model="sortBy.selected"
                  active-class="selected"
                  multiple
                  class="filter-list"
                >
                  <template v-for="(item, index) in sortBy.list">
                    <v-list-item :key="item.title" class="extra-dense" :ripple="false" @click="orderState(index)">
                      <template v-slot:default>
                        
                        <v-list-item-icon class="mr-2">
                          <v-icon v-if="item.order==='no'" small color="grey" class="filter-icon mt-auto mb-auto">
                            {{ item.icon }}
                          </v-icon>
                          <v-icon v-else small color="primary" class="filter-icon-active mt-auto mb-auto">
                            {{ item.icon }}
                          </v-icon>
                        </v-list-item-icon>

                        <v-list-item-content class="py-1 mt-auto mb-auto">
                          {{ item.label }}
                        </v-list-item-content>

                        <v-list-item-action>
                          <v-icon v-if="item.order != 'no'" small color="dark-grey" :class="['mt-auto', 'mb-auto', {'asc': item.order === 'asc', 'desc': item.order === 'desc',}]">
                            mdi-chevron-up
                          </v-icon>
                        </v-list-item-action>
                      </template>
                    </v-list-item>
                  </template>
                </v-list-item-group>
              </v-list>
            </v-col>
          </v-row>

        </v-col>
      </v-row>
      
    </v-container>
</template>

<script>

export default {
  name: 'DashboardNav',
  components: {

  },
  data: () => ({
    links: [],
    menu: false,
    date: {
      range: [],
      chips: {
        all: true,
        today: false,
        week: false
      },
    },
    tags: {
      focused: false,
      selected: ['all'],
      list: [
          'all',
          'State',
          'Vulnerability',
          'Threat',
          'DDoS',
          'Cyberwar',
          'Java',
          'CVE',
        ],
    },
    filterBy: {
      selected: [],
      list: [
        {
          label: 'active topics',
          icon: 'mdi-message-outline',
        },
        {
          label: 'pinned topics',
          icon: '$awakePin',
        },
        {
          label: 'hot topics',
          icon: 'mdi-star-outline',
        },
        {
          label: 'upvoted topics',
          icon: 'mdi-arrow-up-circle-outline',
        },
      ],
    },
    sortBy: {
      selected: [],
      orderList: ['no', 'asc', 'desc'],
      list: [
        {
          label: 'relevance score',
          icon: 'mdi-star-outline',
          order: 'no',
        },
        {
          label: 'last activity',
          icon: 'mdi-calendar-range-outline',
          order: 'no',
        },
        {
          label: 'new news items',
          icon: 'mdi-file-outline',
          order: 'no',
        },
        {
          label: 'new comments',
          icon: 'mdi-message-outline',
          order: 'no',
        },
        {
          label: 'upvotes',
          icon: 'mdi-arrow-up-circle-outline',
          order: 'no',
        },
      ],
    }
  }),
    computed: {
      dateRangeText () {
        return this.date.range.join(' - ')
      },
    },
    methods: {
      deleteChip(chip) {
        this.tags.selected = this.tags.selected.filter(c => c !== chip)
      },
      dateSelector(elem) {
        this.date.chips[elem] = !this.date.chips[elem]
        if (elem === "all") {
          this.date.chips.today = false;
          this.date.chips.week = false;
          this.date.range = [];
        } else if (elem === "range") {
          this.date.chips.today = false;
          this.date.chips.week = false;
          this.date.chips.all = false;
        } else {
          this.date.chips.all = false;
          this.date.range = [];
        }
      },
      orderState(index) {
        var item = this.sortBy.list[index];
        item.order = this.sortBy.orderList[(this.sortBy.orderList.indexOf(item.order) + 1) % (this.sortBy.orderList).length];
        // if (item.order === "asc") {
        //   item.order = "desc";
        // } else if (item.order === "desc") {
        //   item.order = "no";
        // } else {
        //   item.order = "asc";
        // }
        return item.order;
      }
    },
}
</script>
