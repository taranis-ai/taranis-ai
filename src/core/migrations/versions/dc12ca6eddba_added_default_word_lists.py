"""added default word lists

Revision ID: dc12ca6eddba
Revises: ff127a2a95f4
Create Date: 2022-07-01 23:42:43.486451

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# revision identifiers, used by Alembic.
revision = 'dc12ca6eddba'
down_revision = 'ff127a2a95f4'
branch_labels = None
depends_on = None


class WordListREVdc12ca6eddba(Base):
    __tablename__ = 'word_list'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String(), nullable=False)
    use_for_stop_words = sa.Column(sa.Boolean, default=False)

    def __init__(self, name, description, use_for_stop_words = False):
        self.name = name
        self.description = description
        self.use_for_stop_words = use_for_stop_words


class WordListCategoryREVdc12ca6eddba(Base):
    __tablename__ = 'word_list_category'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String(), nullable=False)
    word_list_id = sa.Column(sa.Integer, sa.ForeignKey('word_list.id'))
    link = sa.Column(sa.String(), nullable=True, default=None)

    def __init__(self, name, description, word_list_id, link):
        self.name = name
        self.description = description
        self.word_list_id = word_list_id
        self.link = link


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    # English

    en_wordlist = WordListREVdc12ca6eddba('Default EN stop list', 'English stop-word list packed with the standard Taranis NG installation.', True)
    session.add(en_wordlist)
    session.commit()

    en_wordlist_category = WordListCategoryREVdc12ca6eddba('Default EN stop list', 'Source: https://www.maxqda.de/hilfe-mx20-dictio/stopp-listen', en_wordlist.id, 'https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/en_complete.csv')
    session.add(en_wordlist_category)
    session.commit()

    # Slovak

    sk_wordlist = WordListREVdc12ca6eddba('Default SK stop list', 'Slovak stop-word list packed with the standard Taranis NG installation.', True)
    session.add(sk_wordlist)
    session.commit()

    sk_wordlist_category = WordListCategoryREVdc12ca6eddba('Default SK stop list', 'Source: https://github.com/stopwords-iso/stopwords-sk/blob/master/stopwords-sk.txt', sk_wordlist.id, 'https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/sk_complete.csv')
    session.add(sk_wordlist_category)
    session.commit()

    # Highlighting

    highlighting_wordlist = WordListREVdc12ca6eddba('Default highlighting wordlist', 'Default highlighting list packed with the standard Taranis NG installation.', False)
    session.add(highlighting_wordlist)
    session.commit()

    highlighting_wordlist_category = WordListCategoryREVdc12ca6eddba('Default highlighting wordlist', 'Sources: https://www.allot.com/100-plus-cybersecurity-terms-definitions/, https://content.teamascend.com/cybersecurity-glossary', highlighting_wordlist.id, 'https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/highlighting.csv')
    session.add(highlighting_wordlist_category)
    session.commit()


def downgrade():
    pass
