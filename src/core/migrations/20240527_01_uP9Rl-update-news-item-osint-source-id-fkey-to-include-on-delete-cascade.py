"""
update news_item_osint_source_id_fkey to include ON DELETE CASCADE
"""

from yoyo import step

__depends__ = {"20240427_01_e4nGV-initial-migration-noop"}

steps = [
    step(
        """
        ALTER TABLE public.news_item DROP CONSTRAINT news_item_osint_source_id_fkey;
        ALTER TABLE ONLY public.news_item
            ADD CONSTRAINT news_item_osint_source_id_fkey FOREIGN KEY (osint_source_id) REFERENCES public.osint_source(id) ON DELETE CASCADE;
    """,
        """
        ALTER TABLE public.news_item DROP CONSTRAINT news_item_osint_source_id_fkey;
        ALTER TABLE ONLY public.news_item
            ADD CONSTRAINT news_item_osint_source_id_fkey FOREIGN KEY (osint_source_id) REFERENCES public.osint_source(id);
    """,
    )
]
