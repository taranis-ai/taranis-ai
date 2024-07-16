"""
update user model
"""

from yoyo import step

__depends__ = {"20240527_01_uP9Rl-update-news-item-osint-source-id-fkey-to-include-on-delete-cascade"}

steps = [
    step("""
        ALTER TABLE public.user DROP CONSTRAINT user_profile_id_fkey;
        ALTER TABLE public.user_permission DROP CONSTRAINT user_permission_permission_id_fkey;
        ALTER TABLE public.user DROP COLUMN profile_id;
        ALTER TABLE public.user ADD COLUMN profile JSON;
        DROP TABLE IF EXISTS public.user_permission;
        DROP TABLE IF EXISTS public.user_profile;
        ALTER TABLE attribute_group_item
        RENAME COLUMN multiple TO required;
        ALTER TABLE report_item_attribute
        RENAME COLUMN multiple TO required;
    """)
]
