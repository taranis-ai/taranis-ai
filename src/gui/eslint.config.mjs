export default {
  extends: [
    "plugin:vue/vue3-recommended",
    "eslint:recommended",
    "@vue/prettier",
    "@vue/eslint-config-prettier",
    "@vue/typescript/recommended",
  ],
  files: ["*.vue", "*.ts", "*.js"],
  languageOptions: {
      ecmaVersion: 2020,
      sourceType: "commonjs",
  },
  rules: {
    camelcase: "off",
    quotes: [
      "error",
      "single",
      { avoidEscape: true },
    ],
    "space-before-function-paren": 0,
    "vue/valid-v-slot": ["error", { allowModifiers: true }],
  },
};
