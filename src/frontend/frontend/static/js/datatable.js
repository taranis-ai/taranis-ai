document.addEventListener('alpine:init', () => {
  Alpine.data('dataTable', () => ({
  data: [],

  items: [],
  filteredItems: [],
  selectedItems: [],
  view: 5,
  searchInput: '',
  pagination: {},
  fuse: null,
  searchKeys: {},

  initData() {
    console.debug('Initializing dataTable: ', this.selectedItems);
    this.filteredItems = this.data
    this.pagination = {
      total: this.data.length,
      lastPage: Math.ceil(this.data.length / this.view),
      perPage: this.view,
      currentPage: 1,
      from: 1,
      to: this.view
    };
    this.fuse = new Fuse(this.data, { keys: this.searchKeys, threshold: 0.2 });
    this.$watch('searchInput', value => this.search(value));
    this.changePage(1)
  },
  updateData(data, selecteditems, searchkeys) {
    this.data = data;
    this.selectedItems = selecteditems;
    this.searchKeys = searchkeys;
    this.initData();
  },
  search(value) {
    if (value.length > 1) {
      const result = this.fuse.search(value);
      this.filteredItems = result.map(r => r.item);
    } else {
      this.filteredItems = this.data;
    }

    this.pagination.total = this.filteredItems.length;
    this.pagination.lastPage = Math.ceil(this.filteredItems.length / this.view) || 1;
    this.changePage(1)
  },
  changePage(page) {
    page = Math.max(1, Math.min(page, this.pagination.lastPage));
    const from = (page - 1) * this.view;
    const to = from + this.view;

    this.items = this.filteredItems.slice(from, to);

    this.pagination.currentPage = page;
    this.pagination.from = from + 1;
    this.pagination.to = Math.min(to, this.pagination.total);
  },
  isEmpty() {
    return !this.pagination.total
  },
  toggleSelectAll() {
    if (this.selectedItems.length === this.items.length) {
      this.selectedItems = []
    } else {
      this.selectedItems = this.items.map(item => item.id)
    }
  }
}));
});
