// Load this after loader.js (<script src="/frontend/static/js/vs/loader.js"></script>)

const scriptUrl = document.currentScript.src;

const vsBase = scriptUrl.replace(
  /\/frontend\/static\/js\/monaco\.js$/,
  "/frontend/static/vendor/js/vs"
);

require.config({
  paths: {
    vs: vsBase,
  },
});

require(["vs/editor/editor.main"], function () {
  monaco.languages.register({
    id: "jinja",
    extensions: [".jinja", ".jinja2", ".j2", ".html"],
    aliases: ["Jinja", "jinja", "jinja2"],
    mimetypes: ["text/jinja", "text/jinja2", "text/html"],
  });

  monaco.languages.setLanguageConfiguration("jinja", {
    comments: {
      blockComment: ["{#", "#}", "<!--", "-->"],
    },
    brackets: [
      ["{%", "%}"],
      ["{{", "}}"],
      ["{#", "#}"],
      ["(", ")"],
      ["[", "]"],
      ["{", "}"],
      ["<!--", "-->"],
      ["<", ">"],
    ],
    autoClosingPairs: [
      { open: "{#", close: " #}" },
      { open: "{%", close: " %}" },
      { open: "{{", close: " }}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: "{", close: "}" },
      { open: '"', close: '"', notIn: ["string", "comment"] },
      { open: "'", close: "'", notIn: ["string", "comment"] },
      // Whitespace control pairs might be tricky here, stick to standard for reliable auto-closing
    ],
    surroundingPairs: [
      { open: '"', close: '"' },
      { open: "'", close: "'" },
      { open: "(", close: ")" },
      { open: "[", close: "]" },
      { open: "{", close: "}" },
      { open: "{%", close: "%}" },
      { open: "{{", close: "}}" },
      { open: "{#", close: "#}" },
      { open: "<", close: ">" },
    ],
    // Add folding markers based on TextMate grammar
    folding: {
      markers: {
        start: new RegExp("^\\s*({%\\s*(block|filter|for|if|macro|raw))"), // Matches start tags
        end: new RegExp(
          "^\\s*({%\\s*(endblock|endfilter|endfor|endif|endmacro|endraw)\\s*%})"
        ), // Matches end tags
      },
    },
    indentationRules: {
      increaseIndentPattern: new RegExp(
        "^\\s*({%\\s*(block|filter|for|if|macro|raw|with|autoescape)\\b(?!.*\\b(endblock|endfilter|endfor|endif|endmacro|endraw|endwith|endautoescape))[^%]*%})"
      ),
      decreaseIndentPattern: new RegExp(
        "^\\s*({%\\s*(elif|else|endblock|endfilter|endfor|endif|endmacro|endraw|endwith|endautoescape)\\b.*?%})"
      ),
    },
  });

  monaco.languages.setMonarchTokensProvider("jinja", {
    defaultToken: "",
    tokenPostfix: ".html",
    ignoreCase: true,
    keywords: [
      "if",
      "else",
      "elif",
      "endif",
      "for",
      "endfor",
      "while",
      "endwhile",
      "do",
      "loop",
      "break",
      "continue",
      "as",
      "with",
      "without",
      "context",
      "include",
      "import",
      "from",
      "true",
      "false",
      "none",
    ],

    operators: [
      "+",
      "-",
      "*",
      "**",
      "/",
      "//",
      "%", // Arithmetic
      "==",
      "<=",
      ">=",
      "<",
      ">",
      "!=", // Comparison
      "=", // Assignment
      "|", // Filter pipe
      "~", // Concatenation
      // 'and', 'or', 'not', 'in', 'is' are keywords but act as operators
    ],
    symbols: /[=><!~?&|+\-*/^%]+/,
    constants: ["true", "false", "none", "True", "False", "None"], // Allow title case for compatibility
    specialVars: ["loop", "super", "self", "varargs", "kwargs", "caller"], // Added caller
    escapes:
      /\\(?:[abfnrtv]|x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|N\{[a-zA-Z ]+\})/,
    // The main tokenizer for our languages
    tokenizer: {
      root: [
          // — 1) Jinja first —
          [/\{#-+/,  { token: "comment.block.jinja", bracket: "@open", next: "@jinjaComment" }],
          [/\{#/,    { token: "comment.block.jinja", bracket: "@open", next: "@jinjaComment" }],
          [/\{\{-+/, { token: "delimiter.variable",   bracket: "@open", next: "@variable" }],
          [/\{\{/,   { token: "delimiter.variable",   bracket: "@open", next: "@variable" }],
          [/\{%-+/,  { token: "delimiter.tag",        bracket: "@open", next: "@block" }],
          [/\{%/,    { token: "delimiter.tag",        bracket: "@open", next: "@block" }],

          // — 2) HTML constructs —
          [/<!DOCTYPE/, "metatag", "@doctype"],
          [/<!--/,      "comment.html", "@htmlComment"],
          [/(<)((?:[\w\-]+:)?[\w\-]+)(\s*)(\/>)/, ["delimiter", "tag", "", "delimiter"]],
          [/(<)(script)/, ["delimiter", { token: "tag", next: "@script" }]],
          [/(<)(style)/,  ["delimiter", { token: "tag", next: "@style" }]],
          [/(<)((?:[\w\-]+:)?[\w\-]+)/, ["delimiter", { token: "tag", next: "@otherTag" }]],
          [/(<\/)((?:[\w\-]+:)?[\w\-]+)/, ["delimiter", { token: "tag", next: "@otherTag" }]],
          [/</, "delimiter"],

          // — 3) HTML text (now stops at { or <) —
          [/[^<{]+/],
      ],

      jinjaComment: [
        [/-?#\}/, { token: "comment.block.jinja", bracket: "@close", next: "@pop" }], // Match closing delimiter with optional whitespace control
        [/[^#\}]+/, "comment.block.jinja"],
        [/#|\}/, "comment.block.jinja"],
      ],

      variable: [
        [
          /-?\}\}/,
          { token: "delimiter.variable", bracket: "@close", next: "@pop" },
        ], // Match closing delimiter with optional whitespace control
        { include: "@expressionInside" },
      ],

      block: [
        [/-?%\}/, { token: "delimiter.tag", bracket: "@close", next: "@pop" }], // Match closing delimiter with optional whitespace control
        { include: "@expressionInside" },
      ],

      // Simplified raw block handling: consumes everything until endraw
      rawblock: [
        [
          /(\{%-?\s*)(endraw)(\s*-?%\})/,
          [
            "delimiter.tag",
            "keyword.control",
            { token: "delimiter.tag", next: "@pop" },
          ],
        ],
        [/[^{%]+/, "comment.block.raw"], // Any character not part of start delimiter
        [/\{%?/, "comment.block.raw"], // Consume parts of delimiters if not endraw
      ],

      expressionInside: [
        // Match keywords, constants, and special variables
        [
          /\b[a-zA-Z_]\w*\b/,
          {
            cases: {
              "@keywords": "keyword.control",
              "@constants": "constant.language",
              "@specialVars": "variable.language",
              "@default": "variable.other",
            },
          },
        ],

        // Numbers (allow underscore separators like in TextMate, though less common in Jinja)
        [/\d+(_\d+)*(\.\d+)?([eE][+\-]?\d+)?/, "number"],

        // Strings
        [
          /"/,
          {
            token: "string.quote.double",
            bracket: "@open",
            next: "@string_double",
          },
        ], // Start double-quoted string
        [
          /'/,
          {
            token: "string.quote.single",
            bracket: "@open",
            next: "@string_single",
          },
        ], // Start single-quoted string

        // Operators and Symbols
        // Specific rule for filter pipe - pushes to a state to identify the filter name
        [
          /\|(?=\s*[a-zA-Z_])/,
          { token: "operators.filter", next: "@filterName" },
        ],
        [
          /@symbols/,
          {
            cases: {
              "@operators": "keyword.operator",
              "@default": "delimiter", // Treat other symbols as delimiters (e.g., ~)
            },
          },
        ],

        // Delimiters: . : , ( ) [ ] { } (pipe handled separately)
        [/\./, "delimiter.accessor"], // Dot for attribute access
        [/[?:,()\[\]{}]/, "delimiter"], // Other delimiters

        // Whitespace
        [/\s+/, "white"],
      ],

      string_double: [
        [/\\\\/, "constant.character.escape"], // 1. Explicit \\
        [/\\"/, "constant.character.escape"], // 2. Explicit \"
        [/@escapes/, "constant.character.escape"], // 3. Other known escapes (modified regex)
        [/\\./, "string.escape.invalid"], // 4. Invalid escapes
        [/[^\\"]+/, "string"], // 5. Regular string content
        [
          /"/,
          { token: "string.quote.double", bracket: "@close", next: "@pop" },
        ], // 6. Closing quote
      ],

      string_single: [
        [/\\\\/, "constant.character.escape"], // 1. Explicit \\
        [/\\'/, "constant.character.escape"], // 2. Explicit \'
        [/@escapes/, "constant.character.escape"], // 3. Other known escapes (modified regex)
        [/\\./, "string.escape.invalid"], // 4. Invalid escapes
        [/[^\\']+/, "string"], // 5. Regular string content
        [
          /'/,
          { token: "string.quote.single", bracket: "@close", next: "@pop" },
        ], // 6. Closing quote
      ],

      // State to capture the filter name after a pipe
      filterName: [
        [/\s+/, "white"], // Eat whitespace before the name
        [/[a-zA-Z_]\w*/, { token: "variable.other.filter", next: "@pop" }], // Filter name itself
        ["", { token: "", next: "@pop" }], // If anything else follows pipe (like another pipe or delimiter), just pop
      ],

      // Handle HTML

      doctype: [
        [/[^>]+/, "metatag.content"],
        [/>/, "metatag", "@pop"],
      ],

      htmlComment: [
        [/-->/, "comment.html", "@pop"],
        [/[^-]+/, "comment.content.html"],
        [/./, "comment.content.html"],
      ],

      otherTag: [
        [/\/?>/, "delimiter", "@pop"],
        [/"([^"]*)"/, "attribute.value"],
        [/'([^']*)'/, "attribute.value"],
        [/[\w\-]+/, "attribute.name"],
        [/=/, "delimiter"],
        [/[ \t\r\n]+/], // whitespace
      ],

      // -- BEGIN <script> tags handling

      // After <script
      script: [
        [/type/, "attribute.name", "@scriptAfterType"],
        [/"([^"]*)"/, "attribute.value"],
        [/'([^']*)'/, "attribute.value"],
        [/[\w\-]+/, "attribute.name"],
        [/=/, "delimiter"],
        [
          />/,
          {
            token: "delimiter",
            next: "@scriptEmbedded",
            nextEmbedded: "text/javascript",
          },
        ],
        [/[ \t\r\n]+/], // whitespace
        [
          /(<\/)(script\s*)(>)/,
          ["delimiter", "tag", { token: "delimiter", next: "@pop" }],
        ],
      ],

      // After <script ... type
      scriptAfterType: [
        [/=/, "delimiter", "@scriptAfterTypeEquals"],
        [
          />/,
          {
            token: "delimiter",
            next: "@scriptEmbedded",
            nextEmbedded: "text/javascript",
          },
        ], // cover invalid e.g. <script type>
        [/[ \t\r\n]+/], // whitespace
        [/<\/script\s*>/, { token: "@rematch", next: "@pop" }],
      ],

      // After <script ... type =
      scriptAfterTypeEquals: [
        [
          /"module"/,
          {
            token: "attribute.value",
            switchTo: "@scriptWithCustomType.text/javascript",
          },
        ],
        [
          /'module'/,
          {
            token: "attribute.value",
            switchTo: "@scriptWithCustomType.text/javascript",
          },
        ],
        [
          /"([^"]*)"/,
          {
            token: "attribute.value",
            switchTo: "@scriptWithCustomType.$1",
          },
        ],
        [
          /'([^']*)'/,
          {
            token: "attribute.value",
            switchTo: "@scriptWithCustomType.$1",
          },
        ],
        [
          />/,
          {
            token: "delimiter",
            next: "@scriptEmbedded",
            nextEmbedded: "text/javascript",
          },
        ], // cover invalid e.g. <script type=>
        [/[ \t\r\n]+/], // whitespace
        [/<\/script\s*>/, { token: "@rematch", next: "@pop" }],
      ],

      // After <script ... type = $S2
      scriptWithCustomType: [
        [
          />/,
          {
            token: "delimiter",
            next: "@scriptEmbedded.$S2",
            nextEmbedded: "$S2",
          },
        ],
        [/"([^"]*)"/, "attribute.value"],
        [/'([^']*)'/, "attribute.value"],
        [/[\w\-]+/, "attribute.name"],
        [/=/, "delimiter"],
        [/[ \t\r\n]+/], // whitespace
        [/<\/script\s*>/, { token: "@rematch", next: "@pop" }],
      ],

      scriptEmbedded: [
        [
          /<\/script/,
          { token: "@rematch", next: "@pop", nextEmbedded: "@pop" },
        ],
        [/[^<]+/, ""],
      ],

      // -- END <script> tags handling

      // -- BEGIN <style> tags handling

      // After <style
      style: [
        [/type/, "attribute.name", "@styleAfterType"],
        [/"([^"]*)"/, "attribute.value"],
        [/'([^']*)'/, "attribute.value"],
        [/[\w\-]+/, "attribute.name"],
        [/=/, "delimiter"],
        [
          />/,
          {
            token: "delimiter",
            next: "@styleEmbedded",
            nextEmbedded: "text/css",
          },
        ],
        [/[ \t\r\n]+/], // whitespace
        [
          /(<\/)(style\s*)(>)/,
          ["delimiter", "tag", { token: "delimiter", next: "@pop" }],
        ],
      ],

      // After <style ... type
      styleAfterType: [
        [/=/, "delimiter", "@styleAfterTypeEquals"],
        [
          />/,
          {
            token: "delimiter",
            next: "@styleEmbedded",
            nextEmbedded: "text/css",
          },
        ], // cover invalid e.g. <style type>
        [/[ \t\r\n]+/], // whitespace
        [/<\/style\s*>/, { token: "@rematch", next: "@pop" }],
      ],

      // After <style ... type =
      styleAfterTypeEquals: [
        [
          /"([^"]*)"/,
          {
            token: "attribute.value",
            switchTo: "@styleWithCustomType.$1",
          },
        ],
        [
          /'([^']*)'/,
          {
            token: "attribute.value",
            switchTo: "@styleWithCustomType.$1",
          },
        ],
        [
          />/,
          {
            token: "delimiter",
            next: "@styleEmbedded",
            nextEmbedded: "text/css",
          },
        ], // cover invalid e.g. <style type=>
        [/[ \t\r\n]+/], // whitespace
        [/<\/style\s*>/, { token: "@rematch", next: "@pop" }],
      ],

      // After <style ... type = $S2
      styleWithCustomType: [
        [
          />/,
          {
            token: "delimiter",
            next: "@styleEmbedded.$S2",
            nextEmbedded: "$S2",
          },
        ],
        [/"([^"]*)"/, "attribute.value"],
        [/'([^']*)'/, "attribute.value"],
        [/[\w\-]+/, "attribute.name"],
        [/=/, "delimiter"],
        [/[ \t\r\n]+/], // whitespace
        [/<\/style\s*>/, { token: "@rematch", next: "@pop" }],
      ],

      styleEmbedded: [
        [/<\/style/, { token: "@rematch", next: "@pop", nextEmbedded: "@pop" }],
        [/[^<]+/, ""],
      ],
    },
  });
});
