export const messages_de = {
  validations: {
    messages: {
      _default: 'Bitte füllen Sie das erforderliche Feld aus'
    },
    custom: {
      username: {
        required: 'Bitte geben Sie Ihren Benutzernamen ein'
      },
      password: {
        required: 'Passwort wird benötigt'
      },
      url: {
        required: 'URL ist erforderlich'
      },
      key: {
        required: 'API-Schlüssel ist erforderlich'
      },
      name: {
        required: 'Name ist erforderlich'
      },
      parameter: {
        required: 'Pflichtfeld'
      },
      password_check: {
        required: 'Passwort wird benötigt',
        confirmed: 'Passwörter sind nicht identisch'
      },
      file: {
        required: 'Datei erforderlich'
      }
    }
  },
  login: {
    title: 'Bitte loggen Sie sich ein',
    username: 'Nutzername',
    password: 'Passwort',
    submit: 'Anmeldung',
    error: 'Benutzername oder Passwort ist falsch',
    backend_error: 'Taranis Core Backend-Fehler'
  },
  user_menu: {
    settings: 'Einstellungen',
    logout: 'Ausloggen',
    dark_theme: 'Dunkles Thema'
  },
  main_menu: {
    enter: 'Eingeben',
    administration: 'Verwaltung',
    assess: 'Bewerten',
    analyze: 'Analysieren',
    publish: 'Publish',
    config: 'Config',
    dashboard: 'Dashboard',
    assets: 'Assets'
  },
  nav_menu: {
    enter: 'Newsbeitrag erstellen',
    newsitems: 'Nachrichten',
    products: 'Produkte',
    publications: 'Veröffentlichungen',
    recent: 'Neueste',
    popular: 'Beliebt',
    favourites: 'Favoriten',
    configuration: 'Aufbau',
    osint_sources: 'OSINT-Quellen',
    osint_source_groups: 'OSINT-Quellgruppen',
    publisher_presets: 'Publisher-Vorgaben',
    collectors: 'Sammler',
    report_items: 'Artikel melden',
    attributes: 'Attribute',
    report_types: 'Berichtstypen',
    product_types: 'Produkttypen',
    roles: 'Rollen',
    acls: 'ACL',
    users: 'Benutzer',
    bots: 'Bots',
    user: 'Benutzer',
    workers: 'Arbeiter',
    organizations: 'Organisationen',
    word_lists: 'Wortlisten',
    asset_groups: 'Asset-Gruppen',
    local: 'Lokal',
    dashboard: 'Dashboard'
  },
  notification: {
    close: 'Schließen'
  },
  enter: {
    create: 'Erstellen',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Nachricht konnte nicht erstellt werden.',
    title: 'Titel',
    review: 'Rezension',
    source: 'Quelle',
    link: 'Verknüpfung',
    successful: 'Die Nachricht wurde erfolgreich erstellt'
  },
  card_item: {
    title: 'Titel',
    created: 'Erstellt',
    collected: 'Gesammelt',
    published: 'Veröffentlicht',
    source: 'Quelle',
    status: 'Status',
    description: 'Beschreibung',
    in_analyze: 'Im Analysieren',
    url: 'URL',
    name: 'Name',
    username: 'Nutzername',
    aggregated_items: 'Aggregierte Nachrichten'
  },
  organization: {
    add_new: 'Neue Organisation hinzufügen',
    edit: 'Organisation bearbeiten',
    add: 'Hinzufügen',
    add_btn: 'Neue hinzufügen',
    save: 'Speichern',
    cancel: 'Stornieren',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Diese Organisation konnte nicht erstellt werden.',
    name: 'Name',
    description: 'Beschreibung',
    street: 'Straße',
    city: 'Stadt',
    zip: 'zip',
    country: 'Land',
    successful: 'Neue Organisation wurde erfolgreich hinzugefügt',
    successful_edit: 'Die Organisation wurde erfolgreich aktualisiert',
    removed: 'Die Organisation wurde erfolgreich entfernt',
    removed_error:
      'Die Organisation wird verwendet und konnte nicht gelöscht werden',
    total_count: 'Organisationen zählen: '
  },
  user: {
    add_new: 'Neuen Benutzer hinzufügen',
    edit: 'Benutzer bearbeiten',
    add: 'Hinzufügen',
    add_btn: 'Neue hinzufügen',
    save: 'Speichern',
    cancel: 'Stornieren',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Dieser Benutzer konnte nicht erstellt werden.',
    username: 'Nutzername',
    name: 'Name',
    successful: 'Neuer Benutzer wurde erfolgreich hinzugefügt',
    successful_edit: 'Benutzer wurde erfolgreich aktualisiert',
    removed: 'Benutzer wurde erfolgreich entfernt',
    removed_error: 'Benutzer wird verwendet und konnte nicht gelöscht werden',
    organization: 'Organisation',
    roles: 'Rollen',
    permissions: 'Berechtigungen',
    total_count: 'Benutzer zählen: ',
    password: 'Passwort',
    password_check: 'Passwort wiederholen'
  },
  osint_source: {
    add_new: 'Neue OSINT-Quelle hinzufügen',
    edit: 'OSINT-Quelle bearbeiten',
    collector: 'Kollektor',
    save: 'Speichern',
    add_btn: 'Neue hinzufügen',
    cancel: 'Stornieren',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Diese OSINT-Quelle konnte nicht gespeichert werden',
    name: 'Name',
    description: 'Beschreibung',
    successful: 'Neue OSINT-Quelle wurde erfolgreich hinzugefügt',
    successful_edit: 'Die OSINT-Quelle wurde erfolgreich aktualisiert',
    removed: 'Die OSINT-Quelle wurde erfolgreich entfernt',
    removed_error:
      'Die OSINT-Quelle wird verwendet und konnte nicht gelöscht werden',
    word_lists: 'Wortlisten',
    type: 'Typ',
    total_count: 'OSINT-Quellen zählen: ',
    osint_source_groups: 'OSINT-Quellgruppen',
    tooltip: {
      group_items: 'Gruppieren Sie Nachrichten in aggregierter Form',
      ungroup_items:
        'Gruppierung von Nachrichtenartikeln aus dem Aggregat aufheben',
      analyze_items: 'Erstellen Sie einen Analysebericht aus Nachrichten',
      read_items: 'Nachrichten als gelesen markieren',
      important_items: 'Nachrichten als wichtig markieren',
      like_items: 'Wie Nachrichtenartikel',
      dislike_items: 'Mag keine Nachrichten',
      delete_items: 'Nachrichten löschen',
      select_all: 'Wählen Sie Alle',
      unselect_all: 'Alles wiederufen'
    },
    notification: {
      success: 'Sammler erfolgreich hinzugefügt'
    },
    dialog_import: 'OSINT-Quellen importieren',
    import: 'Importieren',
    export: 'Export'
  },
  osint_source_group: {
    add_new: 'Fügen Sie eine neue OSINT-Quellgruppe hinzu',
    edit: 'OSINT-Quellgruppe bearbeiten',
    add: 'Neue hinzufügen',
    cancel: 'Stornieren',
    save: 'Speichern',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Diese OSINT-Quellgruppe konnte nicht gespeichert werden',
    name: 'Name',
    description: 'Beschreibung',
    successful: 'Neue OSINT-Quellgruppe wurde erfolgreich hinzugefügt',
    successful_edit: 'Die OSINT-Quellgruppe wurde erfolgreich aktualisiert',
    removed: 'Die OSINT-Quellgruppe wurde erfolgreich entfernt',
    removed_error:
      'Die OSINT-Quellgruppe wird verwendet und konnte nicht gelöscht werden',
    title: 'Titel',
    osint_sources: 'OSINT-Quellen',
    total_count: 'Anzahl der OSINT-Quellgruppen: ',
    default_group: 'Nicht kategorisiert',
    default_group_description:
      'Standardgruppe für nicht kategorisierte OSINT-Quellen'
  },
  role: {
    add_new: 'Neue Rolle hinzufügen',
    edit: 'Rolle bearbeiten',
    add: 'Hinzufügen',
    add_btn: 'Neue hinzufügen',
    cancel: 'Stornieren',
    save: 'Speichern',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Diese Rolle konnte nicht gespeichert werden.',
    name: 'Name',
    description: 'Beschreibung',
    successful: 'Neue Rolle wurde erfolgreich hinzugefügt',
    successful_edit: 'Rolle wurde erfolgreich aktualisiert',
    removed: 'Rolle wurde erfolgreich entfernt',
    removed_error: 'Rolle wird verwendet und konnte nicht gelöscht werden',
    title: 'Titel',
    permissions: 'Berechtigungen',
    total_count: 'Rollen zählen: '
  },
  acl: {
    full_title: 'Zugriffskontrolllisten',
    add_new: 'Neue ACL hinzufügen',
    edit: 'ACL bearbeiten',
    add: 'Hinzufügen',
    add_btn: 'Neue hinzufügen',
    cancel: 'Stornieren',
    save: 'Speichern',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Diese ACL konnte nicht gespeichert werden.',
    name: 'Name',
    description: 'Beschreibung',
    item_type: 'Gegenstandsart',
    item_id: 'Artikel Identifikationsnummer',
    everyone: 'Alle',
    see: 'Sehen',
    access: 'Zugang',
    modify: 'Ändern',
    successful: 'Neue ACL wurde erfolgreich hinzugefügt',
    successful_edit: 'ACL wurde erfolgreich aktualisiert',
    removed: 'ACL wurde erfolgreich entfernt',
    removed_error: 'ACL wird verwendet und konnte nicht gelöscht werden',
    roles: 'Rollen',
    users: 'Benutzer',
    total_count: 'ACL-Zählung: '
  },
  publisher_preset: {
    add_new: 'Neue Publisher-Voreinstellung hinzufügen',
    edit: 'Publisher-Voreinstellung bearbeiten',
    publisher: 'Herausgeber',
    add: 'Hinzufügen',
    save: 'Speichern',
    add_btn: 'Neue hinzufügen',
    cancel: 'Stornieren',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Diese Voreinstellung konnte nicht erstellt werden.',
    name: 'Name',
    description: 'Beschreibung',
    use_for_notifications: 'Für alle globalen Benachrichtigungen verwenden',
    successful: 'Neue Publisher-Voreinstellung wurde erfolgreich hinzugefügt',
    successful_edit:
      'Die Publisher-Voreinstellung wurde erfolgreich aktualisiert',
    removed: 'Publisher-Voreinstellung wurde erfolgreich entfernt',
    removed_error:
      'Publisher-Voreinstellung wird verwendet und konnte nicht gelöscht werden',
    total_count: 'Anzahl der Publisher-Vorgaben: '
  },
  product_type: {
    add_new: 'Neuen Produkttyp hinzufügen',
    edit: 'Neuen Produkttyp bearbeiten',
    presenter: 'Moderator',
    add: 'Hinzufügen',
    save: 'Speichern',
    add_btn: 'Neue hinzufügen',
    cancel: 'Stornieren',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Dieser Produkttyp konnte nicht erstellt werden.',
    name: 'Name',
    description: 'Beschreibung',
    successful: 'Neuer Produkttyp wurde erfolgreich hinzugefügt',
    successful_edit: 'Produkttyp wurde erfolgreich aktualisiert',
    removed: 'Der Produkttyp wurde erfolgreich entfernt',
    removed_error:
      'Der Produkttyp wird verwendet und konnte nicht gelöscht werden',
    total_count: 'Produkttypen zählen: ',
    help: 'Beschreibung der Vorlagenparameter',
    close: 'Schließen',
    choose_report_type:
      'Wählen Sie den Berichtstyp, um seine Parameterbeschreibung anzuzeigen',
    report_items: 'Artikel melden',
    report_items_object: {
      name: 'Name',
      name_prefix: 'Namenspräfix',
      type: 'Berichtselementtyp'
    },
    news_items: 'Nachrichten',
    news_items_object: {
      title: 'Titel',
      review: 'Rezension',
      content: 'Inhalt',
      author: 'Autor',
      source: 'Quelle',
      link: 'Verknüpfung',
      collected: 'Gesammeltes Datum',
      published: 'Veröffentlichungsdatum'
    }
  },
  attribute: {
    add: 'Hinzufügen',
    add_btn: 'Neue hinzufügen',
    add_new: 'Neues Attribut hinzufügen',
    edit: 'Attribut bearbeiten',
    add_attachment: 'Anhang hinzufügen',
    add_value: 'Mehrwert',
    select_attachment: 'Anhang auswählen',
    select_file: 'Datei aussuchen',
    save: 'Speichern',
    cancel: 'Stornieren',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Dieses Attribut konnte nicht erstellt werden',
    name: 'Name',
    description: 'Beschreibung',
    type: 'Typ',
    validator: 'Prüfer',
    validator_parameter: 'Validator-Parameter',
    default_value: 'Standardwert',
    successful: 'Neues Attribut wurde erfolgreich hinzugefügt',
    successful_edit: 'Attribut wurde erfolgreich aktualisiert',
    removed: 'Attribut wurde erfolgreich entfernt',
    removed_error: 'Attribut wird verwendet und konnte nicht gelöscht werden',
    value: 'Wert',
    value_text: 'Werttext',
    tlp_white: 'TLP: WEISS',
    tlp_green: 'TLP: GRÜN',
    tlp_amber: 'TLP: AMBER',
    tlp_red: 'TLP: ROT',
    attribute_parameters: 'Attributparameter',
    attribute_constants: 'Attributkonstanten',
    import_from_csv: 'Aus CSV-Datei importieren',
    new_constant: 'Neue Konstante',
    attribute: 'Attribut',
    attributes: 'Attribute',
    new_attribute: 'Neues Attribut',
    min_occurrence: 'Min. Vorkommen',
    max_occurrence: 'Max. Vorkommen',
    total_count: 'Attribute zählen: ',
    import: 'Importieren',
    load_csv_file: 'CSV-Datei laden',
    file_has_header: 'Datei hat Header',
    search: 'Suchen',
    reload_cpe: 'CPE-Wörterbuch neu laden',
    reload_cve: 'CVE-Wörterbuch neu laden',
    delete_existing: 'Löschen Sie alle vorhandenen Werte',
    select_enum: 'Wählen Sie Konstanter Wert',
    reloading: 'Wörterbuch wird neu geladen...',
    status: 'Status',
    select_date: 'Datum auswählen',
    select_time: 'Wählen Sie Zeit',
    select_datetime: 'Wählen Sie Datum/Uhrzeit aus',
    done: 'Erledigt'
  },
  report_type: {
    add_new: 'Neuen Berichtselementtyp hinzufügen',
    edit: 'Berichtselementtyp bearbeiten',
    add_btn: 'Neue hinzufügen',
    save: 'Speichern',
    cancel: 'Stornieren',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Dieser Berichtselementtyp konnte nicht gespeichert werden',
    name: 'Name',
    description: 'Beschreibung',
    section_title: 'Abschnitt',
    new_group: 'Neue Attributgruppe',
    successful: 'Der neue Berichtselementtyp wurde erfolgreich hinzugefügt',
    successful_edit: 'Berichtselementtyp wurde erfolgreich aktualisiert',
    removed_error:
      'Der Berichtselementtyp wird verwendet und konnte nicht gelöscht werden',
    removed: 'Berichtselementtyp wurde erfolgreich entfernt',
    total_count: 'Anzahl der Berichtstypen: '
  },
  report_item: {
    add_new: 'Neues Berichtselement',
    edit: 'Berichtselement bearbeiten',
    save: 'Speichern',
    cancel: 'Stornieren',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Dieses Berichtselement konnte nicht erstellt werden',
    title: 'Name',
    title_prefix: 'Namenspräfix',
    report_type: 'Berichtselementtyp',
    successful: 'Neues Berichtselement wurde erfolgreich hinzugefügt',
    successful_edit: 'Berichtselement wurde erfolgreich gespeichert',
    removed: 'Berichtselement wurde erfolgreich entfernt',
    removed_error:
      'Berichtselement wird verwendet und konnte nicht gelöscht werden',
    select: 'Wählen Sie Berichtselemente aus',
    select_remote: 'Wählen Sie Berichtselemente von Remote-Knoten aus',
    add: 'Hinzufügen',
    attributes: 'Attribute',
    import_csv: 'CSV importieren',
    import_from_csv: 'CVE/CPE aus CSV importieren',
    delete_existing_codes: 'Löschen Sie vorhandene CVE/CPE-Codes',
    tooltip: {
      sort_time: 'Sortieren Sie die Werte von den neuesten',
      sort_user: 'Zeige zuerst meine Werte, dann andere',
      cvss_detail: 'CVSS-Rechnerdefinition anzeigen',
      enum_selector: 'Wertesuchfenster anzeigen',
      delete_value: 'Wert aus diesem Attribut löschen',
      add_value: 'Fügen Sie diesem Attribut einen neuen Wert hinzu'
    }
  },
  product: {
    add_new: 'Neues Produkt',
    add_btn: 'Neue hinzufügen',
    edit: 'Produkt bearbeiten',
    save: 'Speichern',
    cancel: 'Stornieren',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Dieses Produkt konnte nicht erstellt werden',
    title: 'Titel',
    name: 'Name',
    description: 'Beschreibung',
    report_type: 'Produktart',
    successful: 'Neues Produkt wurde erfolgreich hinzugefügt',
    successful_edit: 'Produkt wurde erfolgreich gespeichert',
    removed: 'Das Produkt wurde erfolgreich entfernt',
    removed_error:
      'Das Produkt wird verwendet und konnte nicht gelöscht werden',
    preview: 'Produktvorschau anzeigen',
    publish: 'Produkt veröffentlichen',
    total_count: 'Produkte zählen: '
  },
  analyze: {
    sort: 'Sortiere nach',
    from: 'Aus',
    to: 'Zu',
    add_new: 'Neue hinzufügen',
    total_count: 'Anzahl der Berichtselemente: ',
    tooltip: {
      filter_completed: 'Abgeschlossene Berichtselemente ein-/ausblenden',
      filter_incomplete: 'Unvollständige Berichtselemente ein-/ausblenden',
      range: {
        ALL: 'Alle Berichtselemente anzeigen',
        TODAY: 'Zeigen Sie die heutigen Berichtselemente an',
        WEEK: 'Berichtselemente für die letzte Woche anzeigen',
        MONTH: 'Berichtselemente für den letzten Monat anzeigen'
      },
      sort: {
        time: {
          ascending:
            'Berichtselemente nach Erstellungsdatum aufsteigend sortieren',
          descending:
            'Berichtselemente nach Erstellungsdatum absteigend sortieren'
        }
      },
      toggle_selection: 'Auswahlmodus für Berichtselemente umschalten',
      delete_items: 'Berichtselemente löschen',
      publish_items: 'Produkt aus Berichtselementen erstellen',
      delete_item: 'Berichtselement löschen',
      publish_item: 'Produkt aus Berichtselement erstellen'
    }
  },
  assess: {
    source: 'Quelle',
    comments: 'Kommentare',
    collected: 'Gesammelt',
    published: 'Veröffentlicht',
    author: 'Autor',
    add_news_item: 'Neuigkeiten hinzufügen',
    select_news_item: 'Wählen Sie Neuigkeiten aus',
    add: 'Hinzufügen',
    aggregate_detail: 'Aggregierte Details',
    aggregate_info: 'Die Info',
    aggregate_title: 'Titel',
    aggregate_description: 'Beschreibung',
    attributes: 'Attribute',
    title: 'Titel',
    description: 'Beschreibung',
    download: 'Herunterladen',
    total_count: 'Nachrichten zählen: ',
    selected_count: 'Ausgewählte Nachrichten zählen: ',
    tooltip: {
      filter_read: 'Ungelesene Nachrichten anzeigen/ausblenden',
      filter_important: 'Wichtige Neuigkeiten ein-/ausblenden',
      filter_relevant: 'Relevante Neuigkeiten ein-/ausblenden',
      filter_in_analyze: 'Nachrichten in der Analyse ein-/ausblenden',
      range: {
        ALL: 'Alle Neuigkeiten anzeigen',
        TODAY: 'Nachrichten von heute anzeigen',
        WEEK: 'Nachrichten der letzten Woche anzeigen',
        MONTH: 'Nachrichten für den letzten Monat anzeigen'
      },
      sort: {
        time: {
          ascending: 'Nachrichten nach Sammeldatum aufsteigend sortieren',
          descending: 'Nachrichten nach Sammeldatum absteigend sortieren'
        },
        relevance: {
          ascending: 'Nachrichten nach Relevanz aufsteigend sortieren',
          descending: 'Nachrichten nach Relevanz absteigend sortieren'
        }
      },
      highlight_wordlist: 'Markieren Sie Wort-für-Wort-Listen',
      toggle_selection: 'Auswahlmodus für Nachrichten umschalten',
      group_items: 'Gruppieren Sie Nachrichten in aggregierter Form',
      ungroup_items:
        'Gruppierung von Nachrichtenartikeln aus dem Aggregat aufheben',
      analyze_items: 'Erstellen Sie einen Analysebericht aus Nachrichten',
      read_items: 'Nachrichten als gelesen markieren',
      important_items: 'Nachrichten als wichtig markieren',
      like_items: 'Wie Nachrichtenartikel',
      dislike_items: 'Mag keine Nachrichten',
      delete_items: 'Nachrichten löschen',
      open_source: 'Quelle der Nachricht in einem neuen Tab öffnen',
      ungroup_item:
        'Gruppierung des Nachrichtenartikels aus dem Aggregat aufheben',
      analyze_item: 'Analysebericht aus Nachricht erstellen',
      read_item: 'Nachricht als gelesen markieren',
      important_item: 'Nachricht als wichtig markieren',
      like_item: 'Wie ein Nachrichtenartikel',
      dislike_item: 'Nachrichten nicht mögen',
      delete_item: 'Nachricht löschen'
    },
    shortcuts: {
      enter_filter_mode: 'Filtermodus aufgerufen. '
    }
  },
  publish: {
    tooltip: {
      range: {
        ALL: 'Alle Produkte anzeigen',
        TODAY: 'Produkte von heute anzeigen',
        WEEK: 'Produkte der letzten Woche anzeigen',
        MONTH: 'Produkte des letzten Monats anzeigen'
      },
      sort: {
        time: {
          ascending: 'Produkte nach Erstellungsdatum aufsteigend sortieren',
          descending: 'Produkte nach Erstellungsdatum absteigend sortieren'
        }
      },
      delete_item: 'Produkt löschen'
    }
  },
  toolbar_filter: {
    search: 'Suchen',
    all: 'Alle',
    today: 'Heute',
    this_week: 'Diese Woche',
    this_month: 'Diesen Monat',
    custom_filter: 'Benutzerdefinierte Filter'
  },
  settings: {
    user_settings: 'Benutzereinstellungen',
    tab_general: 'Allgemein',
    tab_wordlists: 'Wortlisten',
    tab_hotkeys: 'Hotkeys',
    save: 'Speichern',
    close_item: 'Schließen',
    collection_up: 'Nach oben bewegen',
    collection_down: 'Sich abwärts bewegen',
    show_item: 'Zeigen',
    read_item: 'Als gelesen markieren',
    important_item: 'Als wichtig markieren',
    like_item: 'Gefällt mir',
    dislike_item: 'Gefällt mir nicht',
    delete_item: 'Löschen',
    spellcheck: 'Rechtschreibprüfung',
    dark_theme: 'Dunkles Thema',
    locale: 'Sprache',
    press_key: 'Neue Taste drücken für ',
    cancel_press_key: 'Stornieren',
    selection: 'Auswahl',
    group: 'Gruppe',
    ungroup: 'Gruppierung aufheben',
    new_product: 'Neues Produkt',
    story_open: 'Story öffnen'
  },
  word_list: {
    add_new: 'Neue Wortliste hinzufügen',
    edit: 'Wortliste bearbeiten',
    add: 'Hinzufügen',
    add_btn: 'Neue hinzufügen',
    save: 'Speichern',
    cancel: 'Stornieren',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Diese Wortliste konnte nicht gespeichert werden',
    name: 'Name',
    description: 'Beschreibung',
    link: 'URL',
    use_for_stop_words: 'Als Stoppwortliste verwenden',
    successful: 'Neue Wortliste wurde erfolgreich hinzugefügt',
    successful_edit: 'Die Wortliste wurde erfolgreich aktualisiert',
    remove: 'Die Wortliste wurde erfolgreich entfernt',
    removed_error:
      'Die Wortliste wird verwendet und konnte nicht gelöscht werden',
    value: 'Wert',
    new_word: 'Neues Wort',
    words: 'Wörter',
    new_category: 'Neue Kategorie',
    total_count: 'Wortlisten zählen: ',
    file_has_header: 'Datei hat Header',
    import_from_csv: 'Aus CSV-Datei importieren',
    load_csv_file: 'CSV-Datei laden',
    download_from_link: 'Von URL herunterladen',
    import: 'Importieren',
    close: 'Schließen'
  },
  asset_group: {
    add_new: 'Neue Asset-Gruppe hinzufügen',
    edit: 'Asset-Gruppe bearbeiten',
    add: 'Neue hinzufügen',
    cancel: 'Stornieren',
    save: 'Speichern',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Diese Asset-Gruppe konnte nicht gespeichert werden',
    name: 'Name',
    description: 'Beschreibung',
    allowed_users:
      'Erlaubte Benutzer (Wenn keiner ausgewählt ist, sind alle Benutzer zugelassen)',
    successful: 'Neue Asset-Gruppe wurde erfolgreich hinzugefügt',
    successful_edit: 'Asset-Gruppe wurde erfolgreich aktualisiert',
    removed: 'Asset-Gruppe wurde erfolgreich entfernt',
    removed_error:
      'Asset-Gruppe wird verwendet und konnte nicht gelöscht werden',
    total_count: 'Anzahl der Asset-Gruppen: '
  },
  asset: {
    add_new: 'Neuen Vermögenswert hinzufügen',
    add_group_info: 'Bitte fügen Sie eine Asset-Gruppe hinzu',
    edit: 'Inhalt bearbeiten',
    add: 'Neue hinzufügen',
    cancel: 'Stornieren',
    save: 'Speichern',
    validation_error: 'Bitte füllen Sie alle geforderten Felder aus',
    error: 'Dieses Asset konnte nicht gespeichert werden',
    name: 'Name',
    serial: 'Seriennummer',
    description: 'Beschreibung',
    cpe: 'CPE-Code',
    new_cpe: 'CPE-Code hinzufügen',
    cpes: 'CPE-Codes',
    value: 'Wert',
    successful: 'Neues Asset wurde erfolgreich hinzugefügt',
    successful_edit: 'Asset wurde erfolgreich aktualisiert',
    removed: 'Inhalt wurde erfolgreich entfernt',
    removed_error: 'Asset wird verwendet und konnte nicht gelöscht werden',
    total_count: 'Assets zählen: ',
    vulnerabilities: 'Schwachstellen',
    vulnerabilities_count: 'Schwachstellen: ',
    no_vulnerabilities: 'Keine Schwachstellen',
    import_csv: 'CSV importieren',
    import_from_csv: 'CPE aus CSV importieren',
    file_has_header: 'Datei hat Header',
    load_csv_file: 'CSV-Datei laden',
    import: 'Importieren',
    close: 'Schließen'
  },
  drop_zone: {
    default_message:
      'Ziehen Sie Dateien hierher oder klicken Sie, um sie auszuwählen',
    file_description: 'Beschreibung',
    last_updated: 'Letzte Aktualisierung',
    save: 'Speichern',
    download: 'Herunterladen',
    delete: 'Löschen',
    cancel: 'Stornieren',
    attachment_load: 'Anhang laden',
    attachment_detail: 'Anhangsdetail'
  },
  error: {
    aggregate_in_use:
      'Einige der ausgewählten Aggregate oder Nachrichten sind bereits einem Berichtselement zugeordnet',
    server_error: 'Unbekannter Serverfehler...'
  }
}
