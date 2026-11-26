from typing import cast

from flask import Blueprint, Flask, request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.discussion import DISCUSSION_PERMISSIONS, CommentPayload, DiscussionKind
from pydantic import ValidationError
from sqlalchemy import select

from core.config import Config
from core.managers.auth_manager import auth_required
from core.managers.db_manager import db
from core.model.comment import Comment
from core.service.discussion import PARENTS, can_delete_parent, comment_page, recent_discussions, visible_parents


def _page() -> int:
    return max(1, min(100000, request.args.get("page", 1, type=int)))


class Discussions(MethodView):
    @auth_required(list(DISCUSSION_PERMISSIONS.values()))
    def get(self):
        kind = request.args.get("kind")
        if kind is not None and kind not in PARENTS:
            return {"error": "Unknown discussion type"}, 400
        return recent_discussions(current_user, cast(DiscussionKind | None, kind), _page(), 20)


class Comments(MethodView):
    @auth_required(list(DISCUSSION_PERMISSIONS.values()))
    def dispatch_request(self, kind: DiscussionKind, parent_id: str, comment_id: str | None = None):
        if kind not in PARENTS or DISCUSSION_PERMISSIONS[kind] not in current_user.get_permissions():
            return {"error": "Discussion not found"}, 404
        model, parent_key = PARENTS[kind]
        query = visible_parents(kind, current_user).where(model.id == parent_id)
        if request.method not in {"GET", "HEAD"}:
            query = query.with_for_update(of=model, read=True, key_share=True)
        if (parent := db.session.scalars(query).first()) is None:
            return {"error": "Discussion not found"}, 404
        return super().dispatch_request(parent=parent, parent_key=parent_key, comment_id=comment_id)

    def get(self, parent, parent_key, comment_id=None):
        page, limit = (1, 3) if request.args.get("preview") == "true" else (_page(), 20)
        return comment_page(parent, parent_key, current_user, page, limit)

    def post(self, parent, parent_key, comment_id=None):
        comment = Comment()
        comment.author_id = current_user.id
        comment.created_at = Comment.utcnow()
        setattr(comment, parent_key.key, parent.id)
        return self._save(comment, creating=True)

    def patch(self, parent, parent_key, comment_id):
        comment = self._get_comment(parent_key, parent.id, comment_id)
        if comment is None:
            return {"error": "Comment not found"}, 404
        if comment.author_id != current_user.id:
            return {"error": "Only the author can edit this comment"}, 403
        return self._save(comment)

    @staticmethod
    def _save(comment: Comment, *, creating: bool = False):
        try:
            payload = CommentPayload.model_validate(request.get_json(silent=True))
        except ValidationError as exc:
            return {"error": CommentPayload.format_validation_errors(exc)}, 400
        if creating:
            comment.body = payload.body
            db.session.add(comment)
        elif payload.body != comment.body:
            comment.body = payload.body
            comment.edited_at = Comment.utcnow()
        db.session.commit()
        return {"id": comment.id}, 201 if creating else 200

    def delete(self, parent, parent_key, comment_id):
        comment = self._get_comment(parent_key, parent.id, comment_id)
        if comment is None:
            return {"error": "Comment not found"}, 404
        if comment.author_id != current_user.id and not can_delete_parent(parent, current_user):
            return {"error": "You cannot delete this comment"}, 403
        db.session.delete(comment)
        db.session.commit()
        return {}, 204

    @staticmethod
    def _get_comment(parent_key, parent_id: str, comment_id: str) -> Comment | None:
        return db.session.scalar(select(Comment).where(Comment.id == comment_id, parent_key == parent_id).with_for_update())


def initialize(app: Flask):
    blueprint = Blueprint("discussion", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/discussions")
    blueprint.add_url_rule("", view_func=Discussions.as_view("recent"))
    comments = Comments.as_view("comments")
    blueprint.add_url_rule("/<kind>/<parent_id>", view_func=comments, methods=["GET", "POST"])
    blueprint.add_url_rule("/<kind>/<parent_id>/<comment_id>", view_func=comments, methods=["PATCH", "DELETE"])
    app.register_blueprint(blueprint)
