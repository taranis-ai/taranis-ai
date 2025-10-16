function initChoices(elementID, placeholder = "items", config = {}) {
  const select = document.getElementById(elementID);
  if (!select || typeof Choices === "undefined") {
    return;
  }

  const classNames = {
    containerOuter: ["choices", "!bg-base-200"],
    containerInner: ["choices__inner", "!bg-base-200"],
    input: ["choices__input", "!bg-base-200"],
    inputCloned: ["choices__input--cloned", "!bg-base-200"],
    list: ["choices__list", "!bg-base-200"],
    itemSelectable: ["choices__item--selectable", "!bg-primary-300"],
    itemChoice: ["choices__item--choice", "!bg-base-200"],
    selectedState: ["is-selected", "!bg-primary"],
  };

  const defaultConfig = {
    removeItemButton: true,
    placeholderValue: "Select " + placeholder,
    noResultsText: "No " + placeholder + " found",
    noChoicesText: "No " + placeholder + " to choose from",
    classNames: classNames,
  };

  const finalConfig = Object.assign({}, defaultConfig, config);

  return new Choices(select, finalConfig);
}
