// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

const lightCodeTheme = require('prism-react-renderer/themes/github');
const darkCodeTheme = require('prism-react-renderer/themes/dracula');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Taranis NG Documentation',
  tagline: 'Taranis NG Documentation',
  url: 'https://github.com/sk-cert/Taranis-NG',
  baseUrl: '/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/favicon.ico',
  organizationName: 'sk-cert', // Usually your GitHub org/user name.
  projectName: 'Taranis-NG', // Usually your repo name.

  presets: [
    [
      '@docusaurus/preset-classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          routeBasePath: '/',
          // Please change this to your repo.
          editUrl: 'https://github.com/sk-cert/Taranis-NG/edit/main/doc/',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: 'Taranis NG Documentation',
        logo: {
          alt: 'Taranis NG',
          src: 'img/taranis-logo-shape.svg',
        },
        items: [
          {
            type: 'doc',
            docId: 'intro',
            position: 'left',
            label: 'Documentation',
          },
          {
            href: 'https://github.com/sk-cert/Taranis-NG',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Documentation',
            items: [
              {
                label: 'Get started',
                to: '/',
              },
              {
                label: 'Docker installation',
                to: '/',
              },
              {
                label: 'Configuration',
                to: '/',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'Stack Overflow',
                href: 'https://stackoverflow.com/questions/tagged/taranisng',
              }
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'SK CERT',
                href: 'https://www.sk-cert.sk',
              },
              {
                label: 'GitHub',
                href: 'https://github.com/sk-cert/',
              },
            ],
          },
        ],
        copyright: `Licensed under the EUPL.`,
      },
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
      },
    }),
};

module.exports = config;
