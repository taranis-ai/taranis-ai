<template>
  <filter-navigation
    :search="storyFilter.search"
    :limit="storyFilter.limit || 20"
    @update:search="(value) => (storyFilter.search = value)"
    @update:limit="(value) => (storyFilter.limit = value)"
  >
    <template #appbar>
      <filter-button
        v-if="smAndUp"
        v-model="storyFilter['read']"
        :label="mdAndDown ? '' : 'read'"
        icon="mdi-eye-check-outline"
      />
      <filter-button
        v-if="smAndUp"
        v-model="storyFilter['in_report']"
        :label="mdAndDown ? '' : 'in reports'"
        icon="mdi-google-circles-communities"
      />
    </template>
    <template #navdrawer>
      <!-- scope -->
      <v-row no-gutters class="ma-2 px-2">
        <v-col cols="12" class="py-1">
          <h4>Source</h4>
        </v-col>

        <v-col cols="12" class="pt-1">
          <v-autocomplete
            v-model="storyFilter.group"
            :items="OSINTSourceGroupsList"
            item-title="title"
            item-value="id"
            label="Source Group"
            :hide-details="true"
            variant="outlined"
            clearable
            clear-icon="mdi-close"
            multiple
            density="compact"
            menu-icon="mdi-chevron-down"
          />
        </v-col>

        <v-col cols="12" class="pt-2">
          <v-autocomplete
            v-model="storyFilter.source"
            :items="OSINTSourcesList"
            item-title="title"
            item-value="id"
            label="Source"
            :hide-details="true"
            variant="outlined"
            clearable
            clear-icon="mdi-close"
            multiple
            density="compact"
            menu-icon="mdi-chevron-down"
          />
        </v-col>
      </v-row>

      <v-divider class="my-2 mt-4"></v-divider>

      <v-row no-gutters class="ma-2 mb-0 px-2">
        <v-col cols="7" class="py-1">
          <h4>Filter</h4>
        </v-col>
        <v-col>
          <a
            href="https://taranis.ai/docs/assess/#details"
            target="_blank"
            style="color: grey; text-decoration: none"
          >
            more details
            <v-icon size="x-small" icon="mdi-open-in-new" />
          </a>
        </v-col>

        <v-col cols="12" class="pt-1">
          <date-chips v-model="filter_range" />
        </v-col>

        <v-col cols="12" class="pt-1">
          <date-filter
            v-model="storyFilter.timefrom"
            placeholder="First Day"
            tooltip-text="The Story's creation date, typically matching the oldest News Item's 'published date'"
            :timeto="storyFilter.timeto"
            :default-date="nextEndOfShift"
          />
        </v-col>

        <v-col cols="12" class="pt-1">
          <date-filter
            v-model="storyFilter.timeto"
            placeholder="Last Day"
            tooltip-text="The Story's update date, usually reflecting the latest addition or change"
            :timefrom="storyFilter.timefrom"
            :default-date="new Date()"
          />
        </v-col>
        <v-col cols="12" class="pt-1">
          <tag-filter v-model="storyFilter.tags" />
        </v-col>
      </v-row>

      <v-row no-gutters>
        <v-col cols="12">
          <AssessFilterButtons />
        </v-col>
      </v-row>

      <v-divider class="my-2" />

      <v-row no-gutters class="ma-2 ml-0 px-2">
        <v-col cols="12" class="ml-2 py-1">
          <h4>Sort</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <filter-sort-list v-model="storyFilter.sort" />
        </v-col>
      </v-row>

      <v-divider class="my-2" />

      <v-row no-gutters class="my-2 mb-0 px-2">
        <v-col cols="12" class="mx-2 py-1">
          <h4>Display</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <v-btn
            class="vertical-button toggle-button py-2 px-4 mb-1"
            :class="
              highlight ? 'toggle-button-checked' : 'toggle-button-unchecked'
            "
            value="highlight"
            prepend-icon="mdi-alphabetical-variant"
            :append-icon="highlight ? 'mdi-check-bold' : undefined"
            :variant="highlight ? 'tonal' : 'text'"
            color="primary"
            @click="highlight = !highlight"
          >
            highlight
          </v-btn>
        </v-col>
        <v-col cols="12" class="pt-0">
          <v-tooltip
            activator="parent"
            :text="
              xxl
                ? 'Show Charts in Story Cards'
                : 'Only possible on FullHD screens'
            "
          />
          <v-btn
            :disabled="disableWeekChart"
            class="vertical-button toggle-button py-2 px-4 mb-1"
            :class="
              showWeekChart
                ? 'toggle-button-checked'
                : 'toggle-button-unchecked'
            "
            value="showWeekChart"
            prepend-icon="mdi-chart-bar"
            :append-icon="showWeekChart ? 'mdi-check-bold' : undefined"
            :variant="showWeekChart ? 'tonal' : 'text'"
            color="primary"
            @click="showWeekChart = !showWeekChart"
          >
            show charts
          </v-btn>
        </v-col>
        <v-col cols="12" class="pt-0">
          <v-btn
            class="vertical-button toggle-button py-2 px-4 mb-1"
            :class="
              compactView ? 'toggle-button-checked' : 'toggle-button-unchecked'
            "
            value="compactView"
            prepend-icon="mdi-view-compact-outline"
            :append-icon="compactView ? 'mdi-check-bold' : undefined"
            :variant="compactView ? 'tonal' : 'text'"
            color="primary"
            @click="setCompactView"
          >
            compact view
          </v-btn>
        </v-col>
      </v-row>

      <v-divider class="my-2 mt-2 mb-0"></v-divider>
      <v-row no-gutters class="my-2 mr-0 px-2 pb-1">
        <v-col cols="12" class="py-2">
          <v-btn
            color="primary"
            prepend-icon="mdi-reload"
            block
            @click="resetFilter()"
          >
            reset filter
            <v-tooltip activator="parent" location="start" text="[ctrl+esc]" />
          </v-btn>
        </v-col>
        <v-col cols="12" class="py-2">
          <v-btn
            color="primary"
            block
            to="enter"
            prepend-icon="mdi-pencil-outline"
          >
            create new item
            <v-tooltip activator="parent" location="start" text="[ctrl+m]" />
          </v-btn>
        </v-col>
      </v-row>
    </template>
  </filter-navigation>
</template>

<script>
import dateChips from '@/components/assess/dateChips.vue'
import dateFilter from '@/components/common/filter/dateFilter.vue'
import tagFilter from '@/components/common/filter/tagFilter.vue'
import filterButton from '@/components/common/filter/filterButton.vue'
import AssessFilterButtons from '@/components/assess/AssessFilterButtons.vue'
import filterSortList from '@/components/common/filter/filterSortList.vue'
import FilterNavigation from '@/components/common/FilterNavigation.vue'
import { computed, onBeforeMount } from 'vue'
import { useFilterStore } from '@/stores/FilterStore'
import { useAssessStore } from '@/stores/AssessStore'
import { useUserStore } from '@/stores/UserStore'
import { storeToRefs } from 'pinia'
import { useDisplay } from 'vuetify'

export default {
  name: 'AssessNav',
  components: {
    dateChips,
    dateFilter,
    tagFilter,
    filterSortList,
    filterButton,
    FilterNavigation,
    AssessFilterButtons
  },
  setup() {
    const assessStore = useAssessStore()
    const filterStore = useFilterStore()
    const userStore = useUserStore()

    const { OSINTSourceGroupsList, OSINTSourcesList } = storeToRefs(assessStore)
    const { mdAndDown, smAndUp, xxl } = useDisplay()

    const {
      storyFilter,
      highlight,
      showWeekChart,
      compactView,
      compactViewSetByUser
    } = storeToRefs(filterStore)

    const { nextEndOfShift } = storeToRefs(userStore)

    const filter_range = computed({
      get() {
        return undefined
      },
      set(value) {
        console.debug('filter_range', value)
        const now = new Date()
        switch (value) {
          case 'shift': {
            storyFilter.value.timefrom = nextEndOfShift.value.toISOString()
            break
          }
          case 'week': {
            const dayOfWeek = now.getDay()
            const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
            now.setDate(now.getDate() + diffToMonday)
            now.setHours(0, 0, 0, 0) // Set hours to 00:00
            storyFilter.value.timefrom = now.toISOString()
            break
          }
          case '24h': {
            const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000)
            storyFilter.value.timefrom = yesterday.toISOString()
            break
          }
        }
      }
    })

    const disableWeekChart = computed(() => {
      return !xxl.value || compactView.value
    })

    onBeforeMount(async () => {
      assessStore.updateOSINTSourceGroupsList()
      assessStore.updateOSINTSources()
    })

    function resetFilter() {
      assessStore.resetFilter()
    }

    function setCompactView() {
      compactView.value = !compactView.value
      compactViewSetByUser.value = true
    }

    return {
      xxl,
      mdAndDown,
      smAndUp,
      highlight,
      showWeekChart,
      compactView,
      filter_range,
      disableWeekChart,
      nextEndOfShift,
      OSINTSourcesList,
      OSINTSourceGroupsList,
      storyFilter,
      resetFilter,
      setCompactView
    }
  }
}
</script>

<style lang="scss">
button {
  display: flex !important;
}

.toggle-button {
  width: 100%;
}
.toggle-button-unchecked {
  color: black !important;
}
</style>
