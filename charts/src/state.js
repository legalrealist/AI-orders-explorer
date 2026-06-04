var state = {
  dataBase: window.__DATA_BASE || './data',
  data: [],
  filtered: [],
  selectedJudge: null,
  chips: new Set(),
  judgeSearch: null,
  barData: [],
  barFiltered: [],
  barSearch: null,
  listPage: 0,
  pageSize: 100,
  lastGroups: [],
  lastIntlData: [],
  searchTimer: null,
};
export default state;
