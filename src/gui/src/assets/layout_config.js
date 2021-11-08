/* GLOBAL LAYOUT CONFiGURATOR */
/* !!! WORK iN PROGRESS - PLEASE, DON'T EDiT THiS FilE, WHiLE THiS COMMENT EXiSTS !!! */

const dialogs = {
    FULLSCREEN: {
        persistent: true,
        noClickAnimation: true,
        fullscreen: true,
        hideOverlay: true,
        transition: "dialog-bottom-transition"
    },
    MODAL: {
        persistent: true,
        noClickAnimation: true,
        maxWidth: 640
    },
    CONFIRM: {
        persistent: true,
        noClickAnimation: true,
        maxWidth: 380
    },
    ROW: {
        WINDOW: {
            align: "center",
            justify: "end"
        }
    },
    TOOLBAR: {
        dense: true,
        tile: true,
        dark: true,
        color: "primary"
    },
    BASEMENT: {
        flat: true
    }
};
const toolbars = {
    FILTER: {
        CONTAINER: {
            fluid: true,
            class: "ma-0 pa-0 pb-1 cx-toolbar-filter primary"
        },
        ROW: {
            align: "center",
            noGutters: true,
            class: "px-4"
        },
        COL: {
            LEFT:{
                align: "left",
                class: "py-0"
            },
            MIDDLE: {
                align: "center",
                class: "py-0"
            },
            RIGHT: {
                align: "right",
                class: "py-0"
            },
            SELECTOR: {
                align: "left",
                class: "my-1 py-0"
            },
            INFO: {
                align: "left",
                class: "py-0 caption"
            }
        },
        GROUP: {
            DAYS: {
                activeClass: "info",
                color: "primary",
                mandatory: true,
                class: "float-left"
            },
            FAVORITES: {
                activeClass: "warning",
                multiple: true,
                class: "float-left"
            },
            SORT: {
                activeClass: "success",
                color: "",
                mandatory: true,
                class: "float-right"
            }
        },
        CHIP: {
            GROUP: {
                small: true,
                label: true,
                class: "px-0 mr-1"
            }
        },
        ICON: {
            CHIPS_SEPARATOR: {
                center: true,
                small: true,
                color: "grey lighten-1",
                class: "pt-2 pr-1 float-left"
            },
            SELECTOR_SEPARATOR: {
                center: true,
                small: true,
                color: "grey lighten-1",
                class: "ma-0 pa-0 pt-1 pl-1 float-left"
            },
            FAVORITES_CHIP: {
                small: true,
                center: true,
                class: "px-2"
            },
            SORT_CHIP_A: {
                small: true,
                center: true,
                class: "pl-2"
            },
            SORT_CHIP_B: {
                small: true,
                center: true,
                class: "pr-2"
            },
            SELECTOR: {
                small: true,
                color: "white"
            }
        },
        BUTTON: {
            SELECTOR: {
                small: true,
                icon: true,
                class: "float-left ma-0 pa-0 primary"
            }
        }
    }
};
const buttons = {
    ADD_NEW: {
        depressed: true,
        small: true,
        class: "primary white--text body-2 font-weight-medium ma-0 pa-0 px-3"
    },
    ADD_NEW_IN: {
        depressed: true,
        small: true,
        outlined: false,
        class: "caption font-weight-medium"
    },
    CLOSE_ICON: {
        icon: true,
        dark: true
    }
};
const cards = {
    DEFAULT: {
        CONTAINER: {
            fluid: true,
            class: "card-item pa-0 ma-0"
        },
        HOVER: {
            flat: true,
            class: "card mb-1"
        },
        ROW: {
            CONTENT: {
                justify: "center",
                align: "center"
            }
        },
        COL: {
            INFO: {
                cols: 4,
                class: "py-0 pl-4 pt-1 pr-4 caption grey--text"
            },
            TITLE: {
                cols: 12,
                class: "pt-2 pb-0 pl-4 headline"
            },
            REVIEW: {
                cols: 12,
                class: "pt-1 pl-4 pb-1 body-2"
            },
            TOOLS: {
                align: "right"
            }
        },
        FOOTER: {
            justify: "center",
            align: "center",
            class: "pl-1 py-0 ma-0"
        },
        LAYOUT: {
            row: true,
            wrap: true,
            class: "rounded"
        },
        TOOLBAR: {
            COMPACT: {
                align: "center"
            }
        }
    }
};
const elements = {
    SEARCH: {
        prependInnerIcon: "mdi-card-search",
        dense: true,
        hideDetails: true,
        class: "mt-0"
    },
};

const classes = {
    toolbar_filter_title: "headline primary--text ma-1 text-uppercase font-weight-light",
    multiselect: "multiselect ma-0 pa-0",
    multiselect_buttons: "float-left pl-1",
    card_offset: "pa-0"
};
const styles = {
    shadow: "box-shadow: 0 1px 5px rgba(0, 0, 0, 0.4);",
    multiselect_active: "background-color: orange !important;",
    z10000: "z-index: 10000;",
    enter_special: "padding-bottom: 0 !important;",
    sticky_filter_toolbar: "position: sticky; top: 48px; z-index: 2;",
    card_selector_zone: "max-width: 64px;",
    card_tag: "max-width: 48px;",
    card_hover_toolbar: "max-width: 32px;",
    card_toolbar: "position: absolute; top: 0; right: 0; width: 25%; min-width: 64px; height: 100%;",
    card_toolbar_strip_bottom: "position: absolute; bottom: 0; right: 0; width: 50%; min-width: 320px; height: 56px;"
};

const icons = {
    SEPARATOR: "mdi-drag-vertical",
    READ: "mdi-eye",
    UNREAD: "mdi-eye-off",
    IMPORTANT: "mdi-star",
    RELEVANT: "mdi-thumb-up",
    IN_ANALYZE: "mdi-file-cog-outline",
    CLOCK: "mdi-clock-outline",
    DESC: "mdi-sort-descending",
    ASC: "mdi-sort-ascending",
    LIKE: "mdi-thumb-up",
    UNLIKE: "mdi-thumb-down",
    GROUP: "mdi-group",
    UNGROUP: "mdi-ungroup",
    ANALYZE: "mdi-file-outline",
    DELETE: "mdi-delete",
    MULTISELECT: "mdi-checkbox-multiple-marked-outline",
    COMPLETED: "mdi-progress-check",
    INCOMPLETED: "mdi-progress-close",
    PLUS: "mdi-plus-circle-outline",
    VULNERABLE: "mdi-alert-octagon-outline",
    ALPHABETICAL: "mdi-alphabet-latin",
    CLOSE: "mdi-close-circle",
    HELP: "mdi-help-circle-outline",
    IMPORT: "mdi-import",
    EXPORT: "mdi-export",
    SELECT_ALL: "mdi-checkbox-multiple-outline",
    UNSELECT_ALL: "mdi-checkbox-multiple-blank-outline"

}

export default Object.freeze({
    DIALOG: dialogs,
    TOOLBAR: toolbars.FILTER,

    BUTTON: buttons,
    CARD: cards.DEFAULT,
    ELEMENT: elements,
    CLASS: classes,
    STYLE: styles,
    ICON: icons
});